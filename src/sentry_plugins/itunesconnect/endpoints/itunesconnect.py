from __future__ import absolute_import

from sentry.utils import json
from sentry.plugins.endpoints import PluginProjectEndpoint


class ItunesConnectAppSyncEndpoint(PluginProjectEndpoint):

    def post(self, request, project, *args, **kwargs):
        client = self.plugin.get_client(project=project)
        app_id = json.loads(request.body.decode('utf-8')).get('app_id')
        apps = set(client.apps_to_sync)
        if app_id in apps:
            apps.remove(app_id)
        else:
            apps.add(app_id)
        client.apps_to_sync = list(apps)
        client.save()
        return self.respond({
            'result': {'apps': client.get_apps()}
        })


class ItunesConnectTestConfigEndpoint(PluginProjectEndpoint):

    def get(self, request, project, *args, **kwargs):
        client = self.plugin.get_client(project=project)
        return self.respond({
            'result': {'apps': client.get_apps()}
        })

    def post(self, request, project, *args, **kwargs):
        client = self.plugin.get_client(project=project)
        result = None
        try:
            api_client = self.plugin.get_api_client(project=project)
            api_client = self.plugin.login(project=project, api_client=api_client)
            result = api_client.get_user_details()
        except Exception as exc:
            error = True
            message = 'There was an error connecting to iTunes Connect.'
            exception = repr(exc)
            self.plugin.reset_client(project=project)
        else:
            error = False
            message = 'No errors returned'
            exception = None
            client.apps = result.get('apps', {})
            client.save()
            result['apps'] = client.get_apps()
            self.plugin.store_client(project=project, api_client=api_client)

        return self.respond({
            'message': message,
            'result': result,
            'error': error,
            'exception': exception,
        })
