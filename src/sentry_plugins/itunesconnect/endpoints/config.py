from __future__ import absolute_import

from django.core.cache import cache

from sentry.utils import json
from sentry.plugins.endpoints import PluginProjectEndpoint
from ..models import Client

class ItunesConnectAppSyncEndpoint(PluginProjectEndpoint):

    def post(self, request, project, *args, **kwargs):
        db_client, _ = Client.objects.get_or_create(
            project=project
        )
        app_id = json.loads(request.body.decode('utf-8')).get('app_id')
        apps = set(db_client.apps_to_sync)
        if app_id in apps:
            apps.remove(app_id)
        else:
            apps.add(app_id)
        db_client.apps_to_sync = list(apps)
        db_client.save()
        teams = db_client.get_teams_with_merged_apps()
        return self.respond({
            'result': teams
        })

class ItunesConnectTestConfigEndpoint(PluginProjectEndpoint):

    def get(self, request, project, *args, **kwargs):
        db_client, _ = Client.objects.get_or_create(
            project=project
        )
        teams = db_client.get_teams_with_merged_apps()
        if teams is not None:
            return self.respond({
                'result': teams,
                'cached': True
            })
        else:
            return self.respond({
                'result': None,
                'cached': False
            })

    def post(self, request, project, *args, **kwargs):
        try:
            client = self.plugin.get_logged_in_client(project=project)
            self.plugin.store_client(project=project, client=client)
            if client.two_fa_request:
                return self.respond({
                    'twoFARequest': True,
                })
            test_results = client.get_user_details()
            db_client, _ = Client.objects.get_or_create(
                project=project
            )
        except Exception as exc:
            error = True
            result = None
            message = 'There was an error connecting to iTunes Connect.'
            exception =  repr(exc)
            cached = False
        else:
            error = False
            message = 'No errors returned'
            exception = None
            cached = True
            db_client.teams = test_results.get('teams', {})
            result = db_client.get_teams_with_merged_apps()
            db_client.save()

        return self.respond({
            'message': message,
            'result': result,
            'error': error,
            'exception': exception,
            'cached': cached,
        })
