from __future__ import absolute_import

from jsonfield import JSONField
from django.db import models
from django.utils import timezone

from sentry.db.models import BaseModel, BaseManager, FlexibleForeignKey


class DSymFile(BaseModel):
    __core__ = False

    objects = BaseManager()
    dsym_file = FlexibleForeignKey('sentry.projectdsymfile')
    app = FlexibleForeignKey('itunesconnect.App')
    version = models.CharField(max_length=32)
    build = models.CharField(max_length=32)
    date_added = models.DateTimeField(default=timezone.now)

    class Meta:
        app_label = 'itunesconnect'
        unique_together = (('dsym_file', 'version', 'build'),)

class AppManager(BaseManager):

    def create_or_update(self, app, project):
        app_id = app['id']
        exsisting_app = App.objects.filter(app_id=app_id, project=project)
        if exsisting_app:
            now = timezone.now()
            exsisting_app.update(
                data=app,
                last_synced=now,
            )
            return exsisting_app

        return BaseManager.create(self,
            app_id=app_id,
            data=app,
            project=project
        )

class App(BaseModel):
    __core__ = False

    objects = AppManager()
    project = FlexibleForeignKey('sentry.Project')
    app_id = models.CharField(max_length=40, unique=True)
    data = JSONField()
    # name = models.CharField(max_length=200, null=True)
    # icon_url = models.CharField(max_length=300, null=True)
    # platforms = models.CharField(max_length=300, null=True)
    # bundle_id = models.CharField(max_length=200, null=True)
    last_synced = models.DateTimeField(default=timezone.now)
    date_added = models.DateTimeField(default=timezone.now)

    class Meta:
        app_label = 'itunesconnect'
