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

OLYMPUS_BASE_URL = 'https://olympus.itunes.apple.com/'
ITC_SERVICE_KEY_URL = urljoin(OLYMPUS_BASE_URL, '/v1/app/config?hostname=itunesconnect.apple.compile')
OLYMPUS_SESSION_URL = urljoin(OLYMPUS_BASE_URL, '/v1/session')

_isk_re = re.compile(r'itcServiceKey\s+=\s+["\'](.*)["\']')


class ItcError(Exception):
    pass


class ItunesConnectClient(object):

    def __init__(self):
        self._reset()

    def _reset(self):
        self._session = SafeSession()
        self._service_key = None
        self._user_details = None
        self._scnt = None
        self._session_id = None
        self.authenticated = False

    def logout(self):
        self._reset()

    def login(self, email=None, password=None):
        if email is None or password is None:
            return

        if self.authenticated:
            # we don't want to login again
            return

        self._get_service_key()

        rv = self._session.post(LOGIN_URL, json={
            'accountName': email,
            'password': password,
            'rememberMe': False,
        }, headers={
            'X-Requested-With': 'XMLHttpRequest',
            'X-Apple-Widget-Key': self._service_key
        })

        self._session_id = rv.headers.get('X-Apple-Id-Session-Id', None)
        self._scnt = rv.headers.get('scnt', None)

        # This is necessary because it sets some further cookies
        rv = self._session.get(urljoin(API_BASE, 'wa'))
        rv.raise_for_status()

        # If we reach this we are authenticated
        self.authenticated = True

    def _get_service_key(self):
        if self._service_key is not None:
            return self._service_key
        rv = self._session.get(ISK_JS_URL)
        match = _isk_re.search(rv.text)
        if match is not None:
            self._service_key = match.group(1)
            return self._service_key
        raise ItcError('Could not find service key')

    def _get_itc_service_key(self):
        rv = self._session.get(ITC_SERVICE_KEY_URL)
        rv.raise_for_status()
        data = rv.json()['data']
        self._service_key = data['authServiceKey']

    def _request_headers(self):
        return {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'X-Apple-Widget-Key': self._service_key,
            'X-Apple-Id-Session-Id': self._session_id,
            'scnt': self._scnt
        }

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
        rv = self._session.get(USER_DETAILS_URL, headers=self._request_headers())
        rv.raise_for_status()
        data = rv.json()['data']

        self._user_details = {
            'apps': self._list_apps(),
            'session': {
                'ds_id': data['sessionToken']['dsId']
            },
            'email': data['userName'],
            'name': data['displayName'],
            'user_id': data['userId'],
        }

    def iter_apps(self):
        """Iterates over all apps the user has access to."""
        return self.get_user_details()['apps']

    def iter_app_builds(self, app):
        """Given an app ID, this iterates over all the builds that exist
        for it.
        """
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

    def get_dsym_url(self, app_id, platform, version, build_id):
        """Looks up the dsym URL for a given build"""
        rv = self._session.get(urljoin(
            API_BASE, 'ra/apps/%s/platforms/%s/trains/%s/builds/%s/details' % (
                app_id, platform, version, build_id)))
        rv.raise_for_status()
        return rv.json()['data']['dsymurl']

    def _list_apps(self):
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
