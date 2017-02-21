from __future__ import absolute_import

from django.conf import settings
from django.core.urlresolvers import reverse
from six.moves.urllib.parse import urlparse, quote

from sentry import options
from sentry.plugins import plugins
from sentry.plugins.bases.notify import NotifyPlugin
from sentry_plugins.utils import get_secret_field_config

from sentry_plugins.base import CorePluginMixin
from .client import ItunesConnectClient
from .endpoints.test_config import ItunesConnectTestConfigEndpoint


class ItunesConnectPlugin(CorePluginMixin, NotifyPlugin):
    description = 'iTunes Connect Debug symbols sync service.'
    slug = 'itunesconnect'
    title = 'iTunes Connect'
    conf_title = title
    conf_key = 'itunesconnect'

    asset_key = 'itunesconnect'
    assets = [
        'dist/itunesconnect.js',
    ]

    def is_configured(self, project, **kwargs):
        return all((self.get_option(k, project) for k in ('email', 'password')))

    def get_client(self, project):
        return ItunesConnectClient(
            email=self.get_option('email', project),
            password=self.get_option('password', project),
        )

    def get_project_urls(self):
        return [
            (r'^test-config/', ItunesConnectTestConfigEndpoint.as_view(plugin=self)),
        ]

    def test_configuration(self, project):
        return self.get_client(project=project).to_json()

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

