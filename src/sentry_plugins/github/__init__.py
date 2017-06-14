from __future__ import absolute_import

from sentry import options

from sentry_plugins.base import assert_package_not_installed

assert_package_not_installed('sentry-github')

try:
    GITHUB_INTEGRATION_APP_ID = options.get('plugins.github.integration_app_id')
    GITHUB_INTEGRATION_PRIVATE_KEY = options.get('plugins.github.integration_private_key')
    GITHUB_INTEGRATION_HOOK_SECRET = options.get('plugins.github.integration_hook_secret')
    GITHUB_APPS_INSTALL_URL = options.get('plugins.github.apps_install_url')
except KeyError:
    raise RuntimeError('Github integrations not properly configured')
