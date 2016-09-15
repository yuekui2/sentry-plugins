from __future__ import absolute_import

import six

import sentry_plugins

from sentry.plugins.bases.issue2 import IssuePlugin2, PluginError

"""
How to get tokens (without OAuth, which we should just block on):

https://www.visualstudio.com/en-us/docs/integrate/get-started/auth/overview
"""

class VisualStudioPlugin(IssuePlugin2):
    author = 'Sentry Team'
    author_url = 'https://github.com/getsentry/sentry-plugins'
    version = sentry_plugins.VERSION
    description = 'Integrate Visual Studio Team Services work items by linking a project."
    resource_links = [
        ('Bug Tracker', 'https://github.com/getsentry/sentry-plugins/issues'),
        ('Source', 'https://github.com/getsentry/sentry-plugins'),
    ]

    slug = 'vsts'
    title = 'Visual Studio'
    conf_title = title
    conf_key = 'vsts'

    def is_configured(self, request, project, **kwargs):
        return bool(self.get_option('repo', project))

    def get_new_issue_fields(self, request, group, event, **kwargs):
        fields = super(VisualStudioPlugin, self).get_new_issue_fields(request, group, event, **kwargs)
        return [{
            'name': 'account',
            'label': 'Account',
            'default': self.get_option('repo', group.project),
            'type': 'text',
            'readonly': True
        }]

    def create_issue(self, request, group, form_data, **kwargs):
        client = self.get_client(group.project)
        response = client.create_work_item(**form_data)

        return json_resp['id']

    def get_issue_label(self, group, issue_id, **kwargs):
        return 'GH-%s' % issue_id

    def get_issue_url(self, group, issue_id, **kwargs):
        # XXX: get_option may need tweaked in Sentry so that it can be pre-fetched in bulk
        repo = self.get_option('repo', group.project)

        return 'https://github.com/%s/issues/%s' % (repo, issue_id)

    def get_configure_plugin_fields(self, request, project, **kwargs):
        return [{
            'name': 'account',
            'label': 'Account',
            'type': 'text',
            'placeholder': 'e.g. sentry.visualstudio.com'
            'help': 'Enter your account name (including the domain).',
        }]
