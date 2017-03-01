from __future__ import absolute_import, print_function

import tempfile
import logging

from django.conf import settings

from sentry import http
from sentry.tasks.base import instrumented_task
from sentry.models import (
    Project, ProjectOption, create_files_from_macho_zip, VersionDSymFile,
    DSymApp
)

logger = logging.getLogger(__name__)

# Time for requests
FETCH_TIMEOUT = 120


def get_project_from_id(project_id):
    return Project.objects.get(id=project_id)


def get_itunes_connect_plugin(project):
    from sentry.plugins import plugins
    for plugin in plugins.for_project(project, version=1):
        if plugin.slug == 'itunesconnect':
            return plugin
    return None


@instrumented_task(name='sentry.tasks.sync_dsyms_from_itunes_connect',
                   time_limit=90,
                   soft_time_limit=60)
def sync_dsyms_from_itunes_connect(**kwargs):
    options = ProjectOption.objects.filter(
        key__in=[
            'itunesconnect:enabled'
        ],
    )

    for opt in options:
        project = get_project_from_id(opt.project_id)
        # TODO sentry should automatically refresh the cache when need
        # this call should not be needed
        ProjectOption.objects.reload_cache(opt.project_id)
        plugin = get_itunes_connect_plugin(project)

        # if itunes plugin is not up and running we do nothing
        if plugin is None:
            return
        if not plugin.is_configured(project):
            return
        if not plugin.is_enabled(project):
            return

        try:
            itc = plugin.get_client(project)
            for app in itc.iter_apps():
                DSymApp.objects.create_or_update(app=app, project=project)
                for build in itc.iter_app_builds(app['id']):
                    fetch_dsym_url.delay(project_id=opt.project_id, app=app, build=build)
        except Exception:
            # plugin.reset_client(project)
            print('reset')


@instrumented_task(
    name='sentry.tasks.fetch_dsym_url',
    queue='itunesconnect')
def fetch_dsym_url(project_id, app, build, **kwargs):
    project = get_project_from_id(project_id)
    plugin = get_itunes_connect_plugin(project)
    itc = plugin.get_client(project)

    app_object = DSymApp.objects.filter(
        app_id=app['id']
    ).first()

    if app is None:
        logger.warning('No app found')
        return

    dsym_files = VersionDSymFile.objects.filter(
        app=app_object,
        build=build['build_id']
    ).first()

    if dsym_files:
        return # we bail out here because we synced this already

    url = itc.get_dsym_url(
        app['id'],
        build['platform'],
        build['version'],
        build['build_id']
    )
    if url is None:
        VersionDSymFile.objects.create(
            app=app_object,
            build=build['build_id'],
            version=build['version'],
        )
        return
    download_dsym(project_id=project_id, url=url, build=build, app_id=app_object.id)


def download_dsym(project_id, url, build, app_id, **kwargs):
    project = get_project_from_id(project_id)
    app_object = DSymApp.objects.filter(
        id=app_id
    ).first()

    # We bump the timeout and reset it after the download
    # itc is kind of slow
    prev_timeout = settings.SENTRY_FETCH_TIMEOUT
    settings.SENTRY_FETCH_TIMEOUT = FETCH_TIMEOUT
    temp = tempfile.TemporaryFile()
    try:
        result = http.fetch_file(
            url=url,
            domain_lock_enabled=False,
            outfile=temp,
            timeout=FETCH_TIMEOUT,
            verify_ssl=True,
        )
        temp.seek(0)
        dsym_project_files = create_files_from_macho_zip(temp, project=project)
        for dsym_project_file in dsym_project_files:
            try:
                VersionDSymFile.objects.create(
                    dsym_file=dsym_project_file,
                    app=app_object,
                    build=build['build_id'],
                    version=build['version'],
                )
            except IntegrityError:
                pass
    except http.CannotFetch:
        logger.warning(
            'Error fetching file from iTunes Connect %r',
            url,
            exc_info=True
        )
    finally:
        settings.SENTRY_FETCH_TIMEOUT = prev_timeout
        temp.close()
