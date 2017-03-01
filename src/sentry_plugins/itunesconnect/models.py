from __future__ import absolute_import

from jsonfield import JSONField
from django.db import models
from django.utils import timezone

from sentry.db.models import BaseModel, BaseManager, FlexibleForeignKey


class Client(BaseModel):
    __core__ = False

    objects = BaseManager()
    project = FlexibleForeignKey('sentry.Project', unique=True)
    apps_to_sync = JSONField()
    itc_client = JSONField()
    last_updated = models.DateTimeField(default=timezone.now)

    class Meta:
        app_label = 'itunesconnect'
