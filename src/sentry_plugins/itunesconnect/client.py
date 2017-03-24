from __future__ import absolute_import

import re

from six.moves.urllib.parse import urljoin
from requests.utils import dict_from_cookiejar, add_dict_to_cookiejar
from sentry.http import SafeSession

BASE_URL = 'https://itunesconnect.apple.com/'
API_BASE = urljoin(BASE_URL, 'WebObjects/iTunesConnect.woa/')
ISK_JS_URL = urljoin(BASE_URL, 'itc/static-resources/controllers/login_cntrl.js')
USER_DETAILS_URL = urljoin(API_BASE, 'ra/user/detail')

APPLEID_BASE_URL = 'https://idmsa.apple.com/'
LOGIN_URL = urljoin(APPLEID_BASE_URL, 'appleauth/auth/signin')
TWOFA_URL = urljoin(APPLEID_BASE_URL, 'appleauth/auth/verify/trusteddevice/securitycode')
TRUST_URL = urljoin(APPLEID_BASE_URL, 'appleauth/auth/2sv/trust')

_isk_re = re.compile(r'itcServiceKey\s+=\s+["\'](.*)["\']')


class ItcError(Exception):
    pass


class ItunesConnectClient(object):

    def __init__(self):
        self._session = SafeSession()
        self._service_key = None
        self._user_details = None
        self._current_team = None
        self._scnt = None
        self._session_id = None
        self.two_fa_request = None
        self.authenticated = False
        self.two_fa_done = False

    def login(self, email=None, password=None):
        if email is None or password is None:
            return

        if self.authenticated:
            # we don't want to login again
            return

        login_url = '%s?widgetKey=%s' % (
            LOGIN_URL,
            self._get_service_key(),
        )
        rv = self._session.post(login_url, json={
            'accountName': email,
            'password': password,
            'rememberMe': False,
        }, headers={
            'X-Requested-With': 'XMLHttpRequest',
        })

        self._session_id = rv.headers.get('X-Apple-Id-Session-Id', None)
        self._scnt = rv.headers.get('scnt', None)

        if rv.headers.get('X-Apple-TwoSV-Trust-Eligible'):
            self.two_fa_request = True
        else:
            self.two_fa_request = False

        # This is necessary because it sets some further cookies
        rv = self._session.get(urljoin(API_BASE, 'wa'))
        rv.raise_for_status()
        # If we reach this we are authenticated
        if (self.two_fa_request is False or self.two_fa_done) \
           and self.authenticated is False:
            self.authenticated = True

    def two_factor(self, security_code):
        rv = self._session.post(TWOFA_URL, json={
            'securityCode': {'code': security_code},
        }, headers={
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'X-Apple-Id-Session-Id': self._session_id,
            'scnt': self._scnt
        })
        rv.raise_for_status()

        if rv.status_code == 204:
            rv = self._session.get(TRUST_URL, headers={
                'X-Apple-Id-Session-Id': self._session_id,
                'scnt': self._scnt
            })
        rv.raise_for_status()
        self.two_fa_done = True

    @classmethod
    def from_json(cls, data):
        """Creates an Itc object from json."""
        rv = cls()

        val = data.get('service_key')
        if val is not None:
            rv._service_key = val

        val = data.get('session_id')
        if val is not None:
            rv._session_id = val

        val = data.get('scnt')
        if val is not None:
            rv._scnt = val

        val = data.get('two_fa_request')
        if val is not None:
            rv.two_fa_request = val

        val = data.get('two_fa_done')
        if val is not None:
            rv.two_fa_done = val

        val = data.get('authenticated')
        if val is not None:
            rv.authenticated = val

        val = data.get('cookies')
        if val:
            add_dict_to_cookiejar(rv._session.cookies, val)

        return rv

    def to_json(self, ensure_user_details=True):
        """Converts an ITC into a JSON object for caching."""
        return {
            'service_key': self._service_key,
            'scnt': self._scnt,
            'session_id': self._session_id,
            'two_fa_request': self.two_fa_request,
            'two_fa_done': self.two_fa_done,
            'authenticated': self.authenticated,
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
        rv = self._session.get(USER_DETAILS_URL)
        rv.raise_for_status()
        data = rv.json()['data']
        teams = []
        apps = []
        for acnt in data['associatedAccounts']:
            team_id = acnt['contentProvider']['contentProviderId']
            apps.append(self._list_apps(team_id, data['sessionToken']['dsId']))

        for app in apps:
            for acnt in data['associatedAccounts']:
                team_id = acnt['contentProvider']['contentProviderId']
                if team_id == app[0]:
                    teams.append({
                        'id': team_id,
                        'name': acnt['contentProvider']['name'],
                        'roles': acnt['roles'],
                        'apps': app[1],
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

    def iter_app_builds(self, app, team_id):
        """Given an app ID, this iterates over all the builds that exist
        for it.
        """
        self._select_team(team_id)

        for platform in app['platforms']:
            rv = self._session.get(urljoin(
                API_BASE, 'ra/apps/%s/buildHistory?platform=%s' % (
                    app['id'], platform)))
            rv.raise_for_status()
            trains = rv.json()['data']['trains']
            for train in trains:
                if train.get('items') is None:
                    app_builds = self._fetch_build_history_with_train(app, train.get('versionString'), platform)
                    for app_build in app_builds:
                        yield {
                            'app_id': app['id'],
                            'platform': app_build['platform'],
                            'version': train['versionString'],
                            'build_id': app_build['buildVersion'],
                        }
                else:
                    for item in train.get('items') or ():
                        yield {
                            'app_id': app['id'],
                            'platform': platform,
                            'version': train['versionString'],
                            'build_id': item['buildVersion'],
                        }

    def _fetch_build_history_with_train(self, app, version, platform):
        rv = self._session.get(urljoin(
            API_BASE, 'ra/apps/%s/trains/%s/buildHistory?platform=%s' % (
                app['id'], version, platform)))
        rv.raise_for_status()
        return rv.json().get('data', {}).get('items', [])

    def get_dsym_url(self, app_id, team_id, platform, version, build_id):
        """Looks up the dsym URL for a given build"""
        self._select_team(team_id)
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

    def _select_team(self, team_id, ds_id=None):
        if self._current_team == team_id:
            return
        if ds_id is None:
            ds_id = self.get_user_details()['session']['ds_id']
        rv = self._session.post(urljoin(
            API_BASE, 'ra/v1/session/webSession'), json={
            'contentProviderId': team_id,
            'dsId': ds_id,
        })
        rv.raise_for_status()
        self._current_team = rv.json()['data']['contentProviderId']

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

        return (self._current_team, rv)

    def close(self):
        self._session.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, tb):
        self.close()
