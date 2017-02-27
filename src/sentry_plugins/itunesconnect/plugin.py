from __future__ import absolute_import

from datetime import timedelta
from django.conf import settings
from django import forms
from django.core.urlresolvers import reverse
from django.core.cache import cache
from six.moves.urllib.parse import urlparse, quote

from sentry import options
from sentry.plugins import plugins
from sentry.plugins.base.v1 import Plugin
from sentry.plugins.base.configuration import react_plugin_config
from sentry_plugins.utils import get_secret_field_config
from sentry.exceptions import PluginError

from sentry_plugins.base import CorePluginMixin
from .client import ItunesConnectClient
from .endpoints.test_config import ItunesConnectTestConfigEndpoint


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
        return 'itc-response:%s' % (project.id)

    def get_itc_client_cache_key(self, project):
        return 'itc-client:%s' % (project.id)

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

    def get_client(self, project, retry=False):
        cache_key = self.get_itc_client_cache_key(project)
        try:
            cached_client = cache.get(cache_key)
            if cached_client:
                return ItunesConnectClient.from_json(cached_client)
            client = ItunesConnectClient(
                email=self.get_option('email', project),
                password=self.get_option('password', project),
            )
            cache.set(cache_key, client.to_json(), 3600)
            return client
        except Exception as exc:
            self.reset_client(project)
            if not retry:
                return self.get_client(project=project, retry=True)
            raise PluginError(exc)

    def reset_client(self, project):
        cache.delete(self.get_itc_client_cache_key(project))
        cache.delete(self.get_itc_response_cache_key(project))

    def get_project_urls(self):
        return [
            (r'^test-config/', ItunesConnectTestConfigEndpoint.as_view(plugin=self)),
        ]

    def test_configuration(self, project):
        return self.get_client(project=project)

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

    def get_celerybeat_schedule(self):
        # 'schedule': timedelta(minutes=15),
        return {'sync-dsyms-from-itunes-connect': {
            'task': 'sentry.tasks.sync_dsyms_from_itunes_connect',
            'schedule': timedelta(seconds=30),
            'options': {
                'expires': 300,
            },
        }}

    def get_celery_imports(self):
        return ('sentry_plugins.itunesconnect.tasks.itunesconnect')

    def get_celery_queues(self):
        # [0] == name, [1] == routing_key
        return [('itunesconnect', 'itunesconnect')]

