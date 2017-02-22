from __future__ import absolute_import, print_function

import tempfile
import logging

from django.conf import settings

from sentry import http
from sentry.tasks.base import instrumented_task
from sentry.models import (
    Project, ProjectOption, create_files_from_macho_zip
)
from ..models import App, DSymFile

logger = logging.getLogger(__name__)


def get_project_from_id(project_id):
    return Project.objects.get(id=project_id)


def get_itunes_connect_plugin():
    from sentry.plugins import plugins
    for plugin in plugins:
        if plugin.slug == 'itunesconnect':
            return plugin
    return None


@instrumented_task(name='sentry.tasks.sync_dsyms_from_itunes_connect',
                   time_limit=90,
                   soft_time_limit=60)
def sync_dsyms_from_itunes_connect(**kwargs):
    options = ProjectOption.objects.filter(
        key__in=[
            'itunesconnect:enabled',
            'itunesconnect:email',
            'itunesconnect:password',
        ],
    )
    plugin = get_itunes_connect_plugin()
    for opt in options:
        project = get_project_from_id(opt.project_id)

        if not plugin.is_configured(project) or not plugin.is_enabled():
            logger.warning('Plugin %r for project %r is not configured', plugin, project)
            return

        prev_timeout = settings.SENTRY_SOURCE_FETCH_TIMEOUT
        settings.SENTRY_SOURCE_FETCH_TIMEOUT = 120
        itc = plugin.get_client(project)
        for app in itc.iter_apps():
            App.objects.create_or_update(app=app, project=project)
            for build in itc.iter_app_builds(app['id']):
                fetch_dsym_url.delay(project_id=opt.project_id, app=app, build=build)
        settings.SENTRY_SOURCE_FETCH_TIMEOUT = prev_timeout
    return


@instrumented_task(
    name='sentry.tasks.fetch_dsym_url',
    queue='itunesconnect')
def fetch_dsym_url(project_id, app, build, **kwargs):
    project = get_project_from_id(project_id)
    plugin = get_itunes_connect_plugin()
    itc = plugin.get_client(project)

    app_object = App.objects.filter(
        app_id=app['id']
    ).first()

    if app is None:
        logger.warning('No app found')
        return

    dsym_files = DSymFile.objects.filter(
        app=app_object
    )

    builds_to_fetch = []
    for dsym_file in dsym_files:
        if dsym_file.build == build['build_id']:
            import pprint; pprint.pprint('we bail out here because we synced this already')
            return # we bail out here because we synced this already

    url = itc.get_dsym_url(app['id'], build['platform'], build['version'], build['build_id'])
    download_dsym.delay(project_id=project_id, url=url, build=build, app_id=app_object.id)


@instrumented_task(
    name='sentry.tasks.download_dsym',
    queue='itunesconnect')
def download_dsym(project_id, url, build, app_id, **kwargs):
    project = get_project_from_id(project_id)
    app_object = App.objects.filter(
        id=app_id
    ).first()

    # We bump the timeout and reset it after the download
    # itc is kind of slow
    prev_timeout = settings.SENTRY_SOURCE_FETCH_TIMEOUT
    settings.SENTRY_SOURCE_FETCH_TIMEOUT = 120
    result = http.stream_download_binary(url)
    settings.SENTRY_SOURCE_FETCH_TIMEOUT = prev_timeout

    temp = tempfile.TemporaryFile()
    try:
        temp.write(result.body)
        dsym_project_files = create_files_from_macho_zip(temp, project=project)
        for dsym_project_file in dsym_project_files:
            DSymFile.objects.create(
                dsym_file=dsym_project_file,
                app=app_object,
                build=build['build_id'],
                version=build['version'],
            )
    finally:
        temp.close()
