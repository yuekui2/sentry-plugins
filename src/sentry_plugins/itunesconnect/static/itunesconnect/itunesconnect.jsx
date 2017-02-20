import React from 'react';
import {plugins} from 'sentry';

import Settings from './components/settings';

class ItunesConnect extends plugins.BasePlugin {
    renderSettings(props) {
        const parentSettings = super.renderSettings(props);
        return <Settings plugin={this} {...props}>
            {parentSettings}
        </Settings>;
    }
}

ItunesConnect.displayName = 'ItunesConnect';

plugins.add('itunesconnect', ItunesConnect);

export default ItunesConnect;
