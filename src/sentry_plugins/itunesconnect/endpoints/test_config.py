from __future__ import absolute_import

from sentry.plugins.endpoints import PluginProjectEndpoint


class ItunesConnectTestConfigEndpoint(PluginProjectEndpoint):
    def get(self, request, project, *args, **kwargs):
        return self.respond({
            'message': test_results,
            'error': error,
        })

    def post(self, request, project, *args, **kwargs):
        try:
            test_results = self.plugin.test_configuration(project)
        except Exception as exc:
            error = True
            result = None
            message = 'There was an error connecting to iTunes Connect.'
        else:
            error = False
            result = test_results.get('user_details', None)
            message = 'No errors returned'

        return self.respond({
            'message': message,
            'result': result,
            'error': error,
        })
