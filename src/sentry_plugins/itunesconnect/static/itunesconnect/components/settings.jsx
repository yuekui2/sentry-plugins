import React from 'react';
import {i18n, IndicatorStore, plugins, Switch} from 'sentry';

class Settings extends plugins.BasePlugin.DefaultSettings {
  constructor(props) {
    super(props);

    this.syncAccount = this.syncAccount.bind(this);
    this.handleLoading = this.handleLoading.bind(this);
    this.finishedLoading = this.finishedLoading.bind(this);
    this.fetchData = this.fetchData.bind(this);

    Object.assign(this.state, {
      loading: false,
      sessionExpired: false
    });
  }

  handleLoading() {
    if (this.state.loading !== false) {
      return true;
    }
    this.setState({
      loading: true,
    });
    return false;
  }

  finishedLoading(loadingIndicator) {
    if (loadingIndicator) IndicatorStore.remove(loadingIndicator);
    this.setState({
      loading: false,
    });
  }

  fetchData() {
    super.fetchData();
    this.api.request(`${this.getPluginEndpoint()}test-config/`, {
      success: (data) => {
        this.setState({
          testResults: data,
          sessionExpired: data.sessionExpired
        });
        this.syncAccount();
      }
    });
  }

  syncAccount() {
    if (this.handleLoading()) return;
    let loadingIndicator = IndicatorStore.add(i18n.t('Syncing account...'));

    this.api.request(`${this.getPluginEndpoint()}test-config/`, {
      method: 'POST',
      success: (data) => {
        this.setState({
          testResults: data
        });
      },
      error: (error) => {
        this.setState({
          testResults: {
            error: true,
            message: 'An unknown error occurred while loading this integration.',
          },
        });
      },
      complete: () => this.finishedLoading(loadingIndicator)
    });
  }

  activateApp(appID) {
    if (this.handleLoading()) return;

    this.api.request(`${this.getPluginEndpoint()}sync-app/`, {
      method: 'POST',
      data: {
        app_id: appID,
      },
      success: (data) => {
        this.setState({
          testResults: data,
        });
      },
      complete: () => this.finishedLoading()
    });
  }

  renderApp(app) {
    return (
      <li className="group" key={app.id}>
          <div className="row" key={app.id}>
            <div className="col-xs-8 event-details">
              <div className="event-message">
                <div className="app-icon" style={app.icon_url && {backgroundImage: `url(${app.icon_url})`}} />
                {app.name}
              </div>
              <div className="event-extra">
                <ul>
                  <li>
                    {app.bundle_id}
                  </li>
                </ul>
              </div>
            </div>
            <div className="col-xs-4 event-details">
              <div className="event-message">
                <span className="align-right pull-right" style={{paddingRight: 16}}>
                  <Switch size="lg"
                    isActive={app.active}
                    isLoading={this.state.loading}
                    toggle={this.activateApp.bind(this, app.id)} />
                </span>
              </div>
            </div>
          </div>
      </li>
    );
  }

  renderSessionExpired() {
    if (!this.state.sessionExpired) {
      return null;
    }
    return (
      <div className="row">
        <div className="col-md-12">
          <div className="alert alert-block alert-error">
            Your session expired, please click on <strong>Sync Account</strong> the re-enable
            the sync again.
          </div>
        </div>
      </div>
    );
  }

  renderContent() {
    if (!this.props.plugin.enabled) {
      return null;
    }
    let hasResult = false;
    if (this.state.testResults && this.state.testResults.result &&
      this.state.testResults.result.apps.length > 0) {
      hasResult = true;
    }

    return (
      <div className="box dashboard-widget">
        <div className="box-header clearfix">
          <div className="row">
            <div className="col-xs-8">
              <h3>{i18n.t('Apps')}</h3>
            </div>
            <div className="col-xs-4 text-right">
              <h3 style={{maxWidth: '100%'}}>{i18n.t('Sync App')}</h3>
            </div>
          </div>
        </div>
        <div className="box-content">
          <div className="tab-pane active">
              {hasResult &&
                <ul className="group-list group-list-small">
                  {this.state.testResults.result.apps.map((app) => {
                    return this.renderApp(app);
                  })}
                </ul>
              }
          </div>
        </div>
      </div>
    );
  }

  render() {
    return (
      <div>
        <div className="ref-itunesconnect-settings">
          {this.props.children}
        </div>
        {this.renderSessionExpired()}
        {this.state.testResults &&
          <div className="ref-itunesconnect-test-results">
            {this.state.testResults.error &&
              <div className="alert alert-block alert-error">
                {this.state.testResults.message}
                <pre>{this.state.testResults.exception}</pre>
              </div>
            }
          </div>
        }
        {this.renderContent()}
      </div>
    );
  }
}

export default Settings;
