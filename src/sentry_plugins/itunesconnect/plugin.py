from __future__ import absolute_import

from datetime import timedelta
from django.conf import settings
from django import forms
from django.core.urlresolvers import reverse
from django.core.cache import cache
from six.moves.urllib.parse import urlparse, quote
from hashlib import md5

from sentry import options
from sentry.plugins import plugins
from sentry.plugins.base.v1 import Plugin
from sentry.plugins.base.configuration import react_plugin_config
from sentry_plugins.utils import get_secret_field_config
from sentry.exceptions import PluginError

from sentry_plugins.base import CorePluginMixin
from .client import ItunesConnectClient
from .endpoints.test_config import ItunesConnectTestConfigEndpoint
from .endpoints.security import ItunesConnectSecurityEndpoint
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

    def get_itc_response_cache_key(self, project):
        return 'itc-response:%s%s' % (project.id, self.get_account_hash(project))

    def get_itc_client_cache_key(self, project):
        return 'itc-client:%s%s' % (project.id, self.get_account_hash(project))

    def get_account_hash(self, project):
        return md5(self.get_option('email', project))

    def configure(self, project, request):
        return react_plugin_config(self, project, request)

    def get_plugin_type(self):
        return 'task-runner'

    def can_enable_for_projects(self):
        return True

    def has_project_conf(self):
        return True

    def is_configured(self, project, **kwargs):
        return all((self.get_option(k, project) for k in ('email', 'password')))

    def get_client(self, project):
        try:
            stored_client, _ = Client.objects.get_or_create(
                project=project
            )
            import pprint;
            pprint.pprint('asdasdasd------------')
            pprint.pprint(stored_client.itc_client)
            if stored_client.itc_client:
                import pprint; pprint.pprint('--------- Cached Client')
                return ItunesConnectClient.from_json(stored_client.itc_client)
            return ItunesConnectClient()
        except Exception as exc:
            raise PluginError(exc)

    def reset_client(self, project):
        client, _ = Client.objects.get_or_create(
            project=project
        )
        client.itc_client = None
        client.save()

    def store_client(self, project, client):
        db_client, _ = Client.objects.get_or_create(
            project=project
        )
        db_client.itc_client = client.to_json(ensure_user_details=False)
        db_client.save()

    def get_project_urls(self):
        return [
            (r'^test-config/', ItunesConnectTestConfigEndpoint.as_view(plugin=self)),
            (r'^securitycode/', ItunesConnectSecurityEndpoint.as_view(plugin=self)),
        ]

    def test_configuration(self, project):
        client = self.get_client(project=project)
        import pprint; pprint.pprint(client)
        client.login(
            email=self.get_option('email', project),
            password=self.get_option('password', project)
        )
        return client

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
        return 'itunesconnect'

