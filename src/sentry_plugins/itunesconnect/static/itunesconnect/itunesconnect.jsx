import React from 'react';
import {i18n, plugins} from 'sentry';

import Settings from './components/settings';

class ItunesConnect extends plugins.BasePlugin {
    renderSettings(props) {
        const parentSettings = super.renderSettings(props);
        return (
          <div>
            <div className="alert alert-block alert-info">
              {i18n.t(`We're currently only support accounts without Two-Factor-Authentication.
                We recommend that you create a new iTunes Connect user with only one team and the apps you want to sync.`)}
            </div>
            <Settings plugin={this} {...props}>
                {parentSettings}
            </Settings>
          </div>
        );
    }
}

ItunesConnect.displayName = 'ItunesConnect';

plugins.add('itunesconnect', ItunesConnect);

export default ItunesConnect;
