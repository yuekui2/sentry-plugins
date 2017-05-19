from __future__ import absolute_import

from django.db import models

from sentry.db.models import Model, BoundedPositiveIntegerField, FlexibleForeignKey


class GitHubInstallation(Model):
    __core__ = False
    organization = FlexibleForeignKey('sentry.Organization', null=True)
    installation_id = BoundedPositiveIntegerField(unique=True)
    account_name = models.CharField(max_length=100)
    account_id = BoundedPositiveIntegerField()

    class Meta:
        app_label = 'github'
        db_table = 'github_installation'

    def is_configured(self):
        return self.organization is not None
