from __future__ import absolute_import

from datetime import timedelta

from sentry.plugins.base.v1 import Plugin
from sentry.plugins.base.configuration import react_plugin_config
from sentry_plugins.utils import get_secret_field_config
from sentry.exceptions import PluginError

from sentry_plugins.base import CorePluginMixin
from .client import ItunesConnectClient
from .endpoints.itunesconnect import (
    ItunesConnectTestConfigEndpoint, ItunesConnectAppSyncEndpoint
)
from .models import Client


class ItunesConnectPlugin(CorePluginMixin, Plugin):
    description = 'iTunes Connect Debug symbols sync service.'
    slug = 'itunesconnect'
    title = 'iTunes Connect'
    conf_title = title
    conf_key = 'itunesconnect'

    asset_key = 'itunesconnect'
    assets = [
        'dist/itunesconnect.js',
    ]

    def configure(self, project, request):
        return react_plugin_config(self, project, request)

    def get_plugin_type(self):
        return 'task-runner'

    def can_enable_for_projects(self):
        return True

    def has_project_conf(self):
        return True

    def set_option(self, key, value, project=None, user=None):
        super(Plugin, self).set_option(key, value, project, user)
        if key != 'enabled' and project:
            self.reset_client(project)

    def reset_options(self, project=None, user=None):
        super(Plugin, self).reset_options(project, user)
        self.reset_client(project=project, full_reset=True)

    def is_configured(self, project, **kwargs):
        return all((self.get_option(k, project) for k in ('email', 'password')))

    def get_client(self, project):
        client, _ = Client.objects.get_or_create(
            project=project
        )
        return client

    def get_api_client(self, project):
        try:
            stored_client, _ = Client.objects.get_or_create(
                project=project
            )
            if (stored_client.itc_client and
               stored_client.itc_client.get('authenticated')):
                return ItunesConnectClient.from_json(stored_client.itc_client)
            return ItunesConnectClient()
        except Exception as exc:
            raise PluginError(exc)

    def reset_client(self, project, full_reset=False):
        client, _ = Client.objects.get_or_create(
            project=project
        )
        client.itc_client = {}
        if full_reset:
            client.apps = {}
            client.apps_to_sync = {}
        client.save()

    def store_client(self, project, api_client):
        itc_client, _ = Client.objects.get_or_create(
            project=project
        )
        itc_client.itc_client = api_client.to_json(ensure_user_details=False)
        itc_client.save()
        return itc_client

    def get_project_urls(self):
        return [
            (r'^test-config/', ItunesConnectTestConfigEndpoint.as_view(plugin=self)),
            (r'^sync-app/', ItunesConnectAppSyncEndpoint.as_view(plugin=self))
        ]

    def login(self, project, api_client):
        api_client.login(
            email=self.get_option('email', project),
            password=self.get_option('password', project)
        )
        return api_client

    def get_config(self, project, **kwargs):
        password = self.get_option('password', project)
        secret_field = get_secret_field_config(password,
                                               'Enter your iTunes Connect password.')
        secret_field.update({
            'name': 'password',
            'label': 'Password',
            'help': 'Enter the password of the iTunes Connect user.'
        })

        return [{
            'name': 'email',
            'label': 'Email',
            'type': 'email',
            'required': True,
            'help': 'Enter the email of the iTunes Connect user.'
        }, secret_field]

    def get_cron_schedule(self):
        # 'schedule': timedelta(minutes=15),
        return {'sync-dsyms-from-itunes-connect': {
            'task': 'sentry.tasks.sync_dsyms_from_itunes_connect',
            'schedule': timedelta(seconds=30),
            'options': {
                'expires': 300,
            },
        }}

    def get_worker_imports(self):
        return ['sentry_plugins.itunesconnect.tasks.itunesconnect']

    def get_worker_queues(self):
        return ['itunesconnect']
