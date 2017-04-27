from __future__ import absolute_import

from sentry.utils import json
from sentry.plugins.endpoints import PluginProjectEndpoint
from ..models import Client


class ItunesConnectAppSyncEndpoint(PluginProjectEndpoint):

    def post(self, request, project, *args, **kwargs):
        itc_client, _ = Client.objects.get_or_create(
            project=project
        )
        app_id = json.loads(request.body.decode('utf-8')).get('app_id')
        apps = set(itc_client.apps_to_sync)
        if app_id in apps:
            apps.remove(app_id)
        else:
            apps.add(app_id)
        itc_client.apps_to_sync = list(apps)
        itc_client.save()
        teams = itc_client.get_teams_with_merged_apps()
        return self.respond({
            'result': teams
        })


class ItunesConnectTestConfigEndpoint(PluginProjectEndpoint):

    def _add_meta_info(self, response, itc_client):
        session_expired = False
        if len(itc_client.itc_client) == 0 and len(itc_client.teams) > 0:
            session_expired = True
        response.update({
            'twoFactorEnabled': itc_client.itc_client.get('two_fa_done', False),
            'sessionExpired': session_expired
        })
        return response

    def get(self, request, project, *args, **kwargs):
        itc_client, _ = Client.objects.get_or_create(
            project=project
        )
        teams = itc_client.get_teams_with_merged_apps()

        return self.respond(
            self._add_meta_info(response={
                'result': teams
            }, itc_client=itc_client)
        )

    def post(self, request, project, *args, **kwargs):
        itc_client, _ = Client.objects.get_or_create(
            project=project
        )
        try:
            client = self.plugin.get_client(project=project)
            client = self.plugin.login(project=project, client=client)
            test_results = client.get_user_details()
        except Exception as exc:
            error = True
            result = None
            message = 'There was an error connecting to iTunes Connect.'
            exception = repr(exc)
        else:
            error = False
            message = 'No errors returned'
            exception = None
            itc_client.teams = test_results.get('teams', {})
            result = itc_client.get_teams_with_merged_apps()
            itc_client.save()

        if client.authenticated is False or \
           (client.first_login_attempt and client.authenticated):
            itc_client = self.plugin.store_client(project=project, client=client)

        if client.two_fa_request:
            return self.respond({
                'twoFARequest': True,
            })

        return self.respond(
            self._add_meta_info(response={
                'message': message,
                'result': result,
                'error': error,
                'exception': exception,
            }, itc_client=itc_client)
        )
