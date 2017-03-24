from __future__ import absolute_import, print_function

import tempfile
import logging

from django.db import IntegrityError
from requests.exceptions import HTTPError

from sentry import http
from sentry.tasks.base import instrumented_task
from sentry.models import (
    Project, ProjectOption, create_files_from_macho_zip, VersionDSymFile,
    DSymApp, DSymPlatform
)
from ..models import Client

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
            itc_client = Client.objects.filter(
                project=project
            ).first()

            if itc_client is None or \
               len(itc_client.apps_to_sync) == 0 or \
               len(itc_client.itc_client) == 0:
                logger.warning('Initial sync not done yet')
                return

            itc = plugin.get_client(project)
            for team in itc_client.teams:
                for app in team.get('apps', []):
                    if itc_client.is_app_active(app.get('id', None)):
                        DSymApp.objects.create_or_update_app(
                            sync_id=app['id'],
                            app_id=app['bundle_id'],
                            project=project,
                            data=app,
                            platform=DSymPlatform.APPLE,
                        )
                        for build in itc.iter_app_builds(app, team['id']):
                            fetch_dsym_url.delay(project_id=opt.project_id, app=app, build=build, team_id=team['id'])
        except Exception as error:
            if isinstance(error, HTTPError):
                if error.response.status_code == 401:
                    logger.warning('iTunes Connect - Not Authorized', extra={'error': error})
                    plugin.reset_client(project)
                    return
            logger.warning('sync_dsyms_from_itunes_connect.fail', extra={'error': error})


@instrumented_task(
    name='sentry.tasks.fetch_dsym_url',
    queue='itunesconnect')
def fetch_dsym_url(project_id, app, build, team_id, **kwargs):
    project = get_project_from_id(project_id)
    plugin = get_itunes_connect_plugin(project)
    itc = plugin.get_client(project)
    # if itunes plugin is not up and running we do nothing
    if plugin is None:
        return
    if not plugin.is_configured(project):
        return
    if not plugin.is_enabled(project):
        return

    dsym_app = DSymApp.objects.filter(
        sync_id=app['id']
    ).first()

    if dsym_app is None:
        logger.warning('No app found')
        return

    dsym_files = VersionDSymFile.objects.filter(
        dsym_app=dsym_app,
        build=build['build_id']
    ).first()

    if dsym_files:
        return  # we bail out here because we synced this already

    url = itc.get_dsym_url(
        app['id'],
        team_id,
        build['platform'],
        build['version'],
        build['build_id']
    )
    if url is None:
        VersionDSymFile.objects.create(
            dsym_app=dsym_app,
            build=build['build_id'],
            version=build['version'],
        )
        logger.warning('Build has no debug symbols')
        return  # this happens if an app does not have any builds/debug symbols
    download_dsym(project_id=project_id, url=url, build=build, dsym_app_id=dsym_app.id)


def download_dsym(project_id, url, build, dsym_app_id, **kwargs):
    project = get_project_from_id(project_id)
    app_object = DSymApp.objects.filter(
        id=dsym_app_id
    ).first()

    temp = tempfile.TemporaryFile()
    try:
        http.fetch_file(
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
                    dsym_app=app_object,
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
        temp.close()
