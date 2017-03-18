from __future__ import absolute_import

import simplejson

from six.moves.urllib.parse import urlencode
from social_auth.utils import dsa_urlopen
from social_auth.backends import BaseOAuth2, OAuthBackend


SLACK_AUTHORIZATION_URL = 'https://slack.com/oauth/authorize'
SLACK_ACCESS_TOKEN_URL = 'https://slack.com/api/oauth.access'
SLACK_AUTH_URL = 'https://slack.com/api/users.identity'


class SlackBackend(OAuthBackend):
    name = 'slack'

    def get_user_details(self, response):
        details = {
            'username': None,
            'email': response['user']['email'],
        }

        name = response['user']['name']
        try:
            # GitHub doesn't separate first and last names. Let's try.
            first_name, last_name = name.split(' ', 1)
        except ValueError:
            details['first_name'] = name
        else:
            details['first_name'] = first_name
            details['last_name'] = last_name
        return details

    def get_user_id(self, details, response):
        return u'{}{}'.format(response['user']['id'], response['team']['id'])


class SlackAuth(BaseOAuth2):
    AUTH_BACKEND = SlackBackend

    AUTHORIZATION_URL = SLACK_AUTHORIZATION_URL
    ACCESS_TOKEN_URL = SLACK_ACCESS_TOKEN_URL
    SETTINGS_KEY_NAME = 'SLACK_CLIENT_ID'
    SETTINGS_SECRET_NAME = 'SLACK_CLIENT_SECRET'
    SCOPE_SEPARATOR = ','

    DEFAULT_SCOPE = ['identity.basic', 'identity.email', 'identity.team']

    def user_data(self, access_token, *args, **kwargs):
        url = '{}?{}'.format(
            SLACK_AUTH_URL, urlencode({
                'token': access_token
            }),
        )

        try:
            data = simplejson.load(dsa_urlopen(url))
        except ValueError:
            data = None

        return data
