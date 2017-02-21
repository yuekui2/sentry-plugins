from __future__ import absolute_import

from django.core.cache import cache

from sentry.plugins.endpoints import PluginProjectEndpoint


class ItunesConnectTestConfigEndpoint(PluginProjectEndpoint):
    def get(self, request, project, *args, **kwargs):
        test_results = cache.get(self.plugin.get_itc_response_cache_key(project))
        if test_results is not None and test_results.get('user_details', None):
            return self.respond({
                'result': test_results.get('user_details', None),
                'cached': True
            })
        else:
            return self.respond({
                'result': None,
                'cached': False
            })

    def post(self, request, project, *args, **kwargs):
        try:
            test_results = self.plugin.test_configuration(project).to_json()
        except Exception as exc:
            error = True
            result = None
            message = 'There was an error connecting to iTunes Connect.'
            exception =  repr(exc)
            cached = False
            cache.delete(self.plugin.get_itc_response_cache_key(project))
        else:
            error = False
            result = test_results.get('user_details', None)
            message = 'No errors returned'
            exception = None
            cached = True
            cache.set(self.plugin.get_itc_response_cache_key(project), test_results, 3600)

        return self.respond({
            'message': message,
            'result': result,
            'error': error,
            'exception': exception,
            'cached': cached,
        })
