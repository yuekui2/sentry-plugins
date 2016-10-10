
from __future__ import absolute_import

from sentry.plugins import plugins
from sentry.rules.actions.base import EventAction


class CreateJIRAIssueAction(EventAction):
    label = 'Create an Issue in JIRA (using default settings)'

    def get_plugin(self):
        return plugins.get('jira')

    def is_enabled(self):
        return self.get_plugin().is_configured(self.project)

    def after(self, event, state):
        yield self.future(self.get_plugin().create_issue_from_automation)
