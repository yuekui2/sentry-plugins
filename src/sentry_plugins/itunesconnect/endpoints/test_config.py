from __future__ import absolute_import

from django.core.cache import cache

from sentry.plugins.endpoints import PluginProjectEndpoint
from ..models import Client

class ItunesConnectTestConfigEndpoint(PluginProjectEndpoint):
    def get(self, request, project, *args, **kwargs):
        db_client, _ = Client.objects.get_or_create(
            project=project
        )
        test_results = db_client.apps_to_sync
        if test_results is not None and test_results.get('teams', None):
            return self.respond({
                'result': test_results,
                'cached': True
            })
        else:
            return self.respond({
                'result': None,
                'cached': False
            })
    def post(self, request, project, *args, **kwargs):
        try:
            client = self.plugin.test_configuration(project=project)
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
            result = test_results
            message = 'No errors returned'
            exception = None
            cached = True
            db_client.apps_to_sync = test_results
            db_client.save()

        return self.respond({
            'message': message,
            'result': result,
            'error': error,
            'exception': exception,
            'cached': cached,
        })
