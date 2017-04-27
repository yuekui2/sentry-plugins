import React from 'react';
import {i18n, IndicatorStore, plugins, Switch, NumberConfirm} from 'sentry';

class Settings extends plugins.BasePlugin.DefaultSettings {
  constructor(props) {
    super(props);

    this.testConfig = this.testConfig.bind(this);
    this.fetchData = this.fetchData.bind(this);
    this.sendAuthCode = this.sendAuthCode.bind(this);

    Object.assign(this.state, {
      testing: false,
      showNumberConfirm: false,
      twoFARequest: false,
      appActivating: false,
      twoFactorEnabled: false,
      sessionExpired: false
    });
  }

  fetchData() {
    super.fetchData();
    this.api.request(`${this.getPluginEndpoint()}test-config/`, {
      success: (data) => {
        this.setState({
          testResults: data,
          twoFactorEnabled: data.twoFactorEnabled,
          sessionExpired: data.sessionExpired
        });
      }
    });
  }

  sendAuthCode(code) {
    this.setState({
      showNumberConfirm: false,
    });
    this.api.request(`${this.getPluginEndpoint()}securitycode/`, {
      method: 'POST',
      data: {
        securitycode: code,
      },
      success: (data) => {
        this.testConfig();
      }
    });
  }

  testConfig() {
    if (this.state.testing !== false) {
      return;
    }
    this.setState({
      testing: true,
    });
    let loadingIndicator = IndicatorStore.add(i18n.t('Syncing account...'));
    this.api.request(`${this.getPluginEndpoint()}test-config/`, {
      method: 'POST',
      success: (data) => {
        if (data.twoFARequest) {
          this.setState({
            showNumberConfirm: true,
          });
        } else {
          this.setState({
            testResults: data,
            twoFactorEnabled: data.twoFactorEnabled,
            sessionExpired: data.sessionExpired
          });
        }
      },
      error: (error) => {
        this.setState({
          testResults: {
            error: true,
            message: 'An unknown error occurred while testing this integration.',
          },
        });
      },
      complete: () => {
        IndicatorStore.remove(loadingIndicator);
        this.setState({
          testing: false,
        });
      }
    });
  }

  activateApp(appID) {
    if (this.state.appActivating) {
      return;
    }
    this.setState({
      appActivating: true,
    });

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
      complete: () => {
        this.setState({
          appActivating: false,
        });
      }
    });
  }

  renderTeam(team) {
    return (
      <li className="group" key={team.id}>
        <div className="row">
          <div className="col-xs-12 event-details">
            <h3 className="truncate">{team.name}</h3>
            <div className="event-message">{team.roles.join(', ')}</div>
            <div className="event-extra">
              <ul>
                <li>
                  ID: {team.id}
                </li>
              </ul>
            </div>
          </div>
        </div>
        {team.apps.map((app) => {
          return (
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
                      isLoading={this.state.appActivating}
                      toggle={this.activateApp.bind(this, app.id)} />
                  </span>
                </div>
              </div>
            </div>
          );
        })}
      </li>
    );
  }

  render2FAInfo() {
    if (!this.state.twoFactorEnabled) {
      return null;
    }
    return (
      <div className="row">
        <div className="col-md-12">
          <div className="alert alert-block alert-info">
            Your account is using <strong>Two-Factor-Authententication</strong>.<br/>
            It is recommend that you create a seperate user for syncing you debug
            symbols.<br/>Sessions to iTunes Connect with Two-Factor-Authententication
            enabled only last about 30 days.<br/>After that period of time you must
            login again.
          </div>
        </div>
      </div>
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

  renderUserDetails() {
    if (!this.props.plugin.enabled) {
      return null;
    }
    let hasResult = false;
    if (this.state.testResults && this.state.testResults.result) {
      hasResult = true;
    }
    return (
      <div className="box dashboard-widget">
        <div className="box-header clearfix">
          <div className="row">
            <div className="col-xs-8">
              <h3>{i18n.t('Team')}</h3>
            </div>
            <div className="col-xs-4">
              <a className="pull-right btn btn-default btn-sm"
                onClick={this.testConfig}
                disabled={this.state.testing}>
                {i18n.t('Sync Account')}
              </a>
            </div>
          </div>
        </div>
        <div className="box-content">
          <div className="tab-pane active">
              {hasResult &&
                <ul className="group-list group-list-small">
                  {this.state.testResults.result.map((team) => {
                      return this.renderTeam(team);
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
        <NumberConfirm digits={6}
          show={this.state.showNumberConfirm}
          onFinished={this.sendAuthCode} />
        <div className="ref-itunesconnect-settings">
          {this.props.children}
        </div>
        {this.render2FAInfo()}
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
        {this.renderUserDetails()}
      </div>
    );
  }
}

export default Settings;
