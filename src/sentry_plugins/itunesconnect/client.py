from __future__ import absolute_import

import re
from six.moves.urllib.parse import urljoin

from requests.utils import dict_from_cookiejar, add_dict_to_cookiejar

from sentry.http import SafeSession


BASE_URL = 'https://itunesconnect.apple.com/'
API_BASE = urljoin(BASE_URL, 'WebObjects/iTunesConnect.woa/')
LOGIN_URL = 'https://idmsa.apple.com/appleauth/auth/signin'
ISK_JS_URL = urljoin(BASE_URL, 'itc/static-resources/controllers/login_cntrl.js')

_isk_re = re.compile(r'itcServiceKey\s+=\s+["\'](.*)["\']')


class ItcError(Exception):
    pass


class ItunesConnectClient(object):

    def __init__(self, email=None, password=None):
        self._session = SafeSession()
        self._service_key = None
        self._user_details = None
        self._current_team = None

        if email is not None:
            login_url = '%s?widgetKey=%s' % (
                LOGIN_URL,
                self._get_service_key(),
            )
            rv = self._session.post(login_url, json={
                'accountName': email,
                'password': password,
                'rememberMe': False,
            })
            rv.raise_for_status()

            # This is necessary because it sets some further cookies
            rv = self._session.get(API_BASE)
            rv.raise_for_status()

    @classmethod
    def from_json(cls, data):
        """Creates an Itc object from json."""
        rv = cls()

        val = data.get('user_details')
        if val is not None:
            rv._user_details = val

        val = data.get('service_key')
        if val is not None:
            rv._service_key = val

        val = data.get('cookies')
        if val:
            add_dict_to_cookiejar(rv._session.cookies, val)

        return rv

    def to_json(self, ensure_user_details=True):
        """Converts an ITC into a JSON object for caching."""
        if ensure_user_details:
            self.get_user_details()
        return {
            'user_details': self._user_details,
            'service_key': self._service_key,
            'cookies': dict_from_cookiejar(self._session.cookies),
        }

    def get_user_details(self):
        """Returns the user details.  If they were not loaded yet this
        triggers a refresh.
        """
        if self._user_details is None:
            self.refresh_user_details()
        return self._user_details

    def refresh_user_details(self):
        """Refreshes the user details."""
        rv = self._session.get(urljoin(API_BASE, 'ra/user/detail'))
        rv.raise_for_status()
        data = rv.json()['data']
        teams = []
        for acnt in data['associatedAccounts']:
            team_id = acnt['contentProvider']['contentProviderId']
            teams.append({
                'id': team_id,
                'name': acnt['contentProvider']['name'],
                'roles': acnt['roles'],
                'apps': self._list_apps(team_id, data['sessionToken']['dsId']),
            })
        self._user_details = {
            'teams': teams,
            'session': {
                'ds_id': data['sessionToken']['dsId']
            },
            'email': data['userName'],
            'name': data['displayName'],
            'user_id': data['userId'],
        }

    def iter_apps(self):
        """Iterates over all apps the user has access to."""
        seen = set()
        for team in self.get_user_details()['teams']:
            for app in team['apps']:
                if app['id'] not in seen:
                    seen.add(app['id'])
                    yield app

    def iter_app_builds(self, app_id):
        """Given an app ID, this iterates over all the builds that exist
        for it.
        """
        rv = self._find_app(app_id)
        if rv is None:
            return
        app, team = rv
        self._select_team(team['id'])

        for platform in app['platforms']:
            rv = self._session.get(urljoin(
                API_BASE, 'ra/apps/%s/buildHistory?platform=%s' % (
                    app_id, platform)))
            rv.raise_for_status()

            trains = rv.json()['data']['trains']
            for train in trains:
                for item in train.get('items') or ():
                    yield {
                        'app_id': app['id'],
                        'platform': platform,
                        'version': train['versionString'],
                        'build_id': item['buildVersion'],
                    }

    def get_dsym_url(self, app_id, platform, version, build_id):
        """Looks up the dsym URL for a given build"""
        rv = self._session.get(urljoin(
            API_BASE, 'ra/apps/%s/platforms/%s/trains/%s/builds/%s/details' % (
                app_id, platform, version, build_id)))
        rv.raise_for_status()
        return rv.json()['data']['dsymurl']

    def _get_service_key(self):
        if self._service_key is not None:
            return self._service_key
        rv = self._session.get(ISK_JS_URL)
        match = _isk_re.search(rv.text)
        if match is not None:
            self._service_key = match.group(1)
            return self._service_key
        raise ItcError('Could not find service key')

    def _find_app(self, app_id):
        for team in self.get_user_details()['teams']:
            for app in team['apps']:
                if app['id'] == app_id:
                    return app, team

    def _select_team(self, team_id, ds_id=None):
        if self._current_team == team_id:
            return
        if ds_id is None:
            ds_id = self.get_user_details()['session']['ds_id']
        self._session.post(urljoin(
            API_BASE, 'ra/v1/session/webSession'), json={
            'contentProviderId': team_id,
            'dsId': ds_id,
        }).raise_for_status()
        self._current_team = team_id

    def _list_apps(self, team_id, ds_id=None):
        self._select_team(team_id, ds_id)

        rv = self._session.get(urljoin(
            API_BASE, 'ra/apps/manageyourapps/summary/v2'))
        rv.raise_for_status()

        apps = rv.json()['data']['summaries']
        rv = []

        for app in apps:
            platforms = set()
            for x in app['versionSets']:
                if x['type'] == 'APP':
                    platforms.add(x['platformString'])
            rv.append({
                'id': app['adamId'],
                'icon_url': app['iconUrl'],
                'bundle_id': app['bundleId'],
                'name': app['name'],
                'platforms': sorted(platforms),
            })

        return rv

    def close(self):
        self._session.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, tb):
        self.close()
