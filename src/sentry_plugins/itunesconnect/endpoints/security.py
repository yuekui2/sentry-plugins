from __future__ import absolute_import

from django.core.cache import cache

from sentry.utils import json
from sentry.plugins.endpoints import PluginProjectEndpoint


class ItunesConnectSecurityEndpoint(PluginProjectEndpoint):
    def post(self, request, project, *args, **kwargs):
        try:
            securitycode = json.loads(request.body.decode('utf-8')).get('securitycode')
            client = self.plugin.get_client(project)
            client.two_factor(securitycode)
            self.plugin.store_client(project=project, client=client)
            return self.respond({ # todo better error
                'result': 'ok'
            })
        except Exception as exc:
            return self.respond({
                'result': 'error'
            })

