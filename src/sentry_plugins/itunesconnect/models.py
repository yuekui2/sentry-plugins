from __future__ import absolute_import

from jsonfield import JSONField
from django.db import models
from django.utils import timezone

from sentry.db.models import (
    BaseModel, BaseManager, FlexibleForeignKey, EncryptedJsonField
)

class Client(BaseModel):
    __core__ = False

    objects = BaseManager()
    project = FlexibleForeignKey('sentry.Project', unique=True)
    teams = EncryptedJsonField()
    itc_client = EncryptedJsonField()
    apps_to_sync = JSONField()
    last_updated = models.DateTimeField(default=timezone.now)

    class Meta:
        app_label = 'itunesconnect'

    def get_teams_with_merged_apps(self):
        rv = []
        for team in self.teams:
            rv_team = []
            for app in team.get('apps', []):
                app['active'] = self.is_app_active(app.get('id', None))
            rv.append(team)
        return rv

    def is_app_active(self, app_id):
        return app_id in self.apps_to_sync


