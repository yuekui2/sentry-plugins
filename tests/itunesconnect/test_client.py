from __future__ import absolute_import

from exam import fixture
from django.test import RequestFactory
from sentry.testutils import PluginTestCase

from sentry_plugins.itunesconnect.plugin import ItunesConnectPlugin


TWO_FA_USERNAME = ''
TWO_FA_PASSWORD = ''


class ItunesConnectClientPluginTest(PluginTestCase):
    @fixture
    def plugin(self):
        return ItunesConnectPlugin()

    @fixture
    def request(self):
        return RequestFactory()

    def test_conf_key(self):
        assert self.plugin.conf_key == 'itunesconnect'

    def test_entry_point(self):
        self.assertAppInstalled('itunesconnect', 'sentry_plugins.itunesconnect')
        self.assertPluginInstalled('itunesconnect', self.plugin)

    def test_is_configured(self):
        self.plugin.set_option('email', 'email@gmail.com', self.project)
        assert self.plugin.is_configured(self.project) is False
        self.plugin.set_option('password', 'email@gmail.com', self.project)
        assert self.plugin.is_configured(self.project) is True

    def test_login(self):
        self.plugin.set_option('email', TWO_FA_USERNAME, self.project)
        self.plugin.set_option('password', TWO_FA_PASSWORD, self.project)
        client = self.plugin.get_client(project=self.project)
        client = self.plugin.login(project=self.project, client=client)
        assert client.needs_two_fa() is True
