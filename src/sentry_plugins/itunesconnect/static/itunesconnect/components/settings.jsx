import React from 'react';
import {i18n, IndicatorStore, LoadingError, LoadingIndicator, plugins} from 'sentry';

class Settings extends plugins.BasePlugin.DefaultSettings {
  constructor(props) {
    super(props);

    this.testConfig = this.testConfig.bind(this);
    this.fetchData = this.fetchData.bind(this);
  }

  fetchData() {
    super.fetchData();
  }

  testConfig() {
    let isTestable = this.props.plugin.isTestable;
    let loadingIndicator = IndicatorStore.add(i18n.t('Testing Connection..'));
    this.api.request(`${this.getPluginEndpoint()}test-config/`, {
      method: 'POST',
      success: (data) => {
        this.setState({
          testResults: data,
        });
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
      }
    });
  }

  renderTeam(team) {
    return (
      <li className="group" key={team.id}>
        <div className="row">
          <div className="col-xs-8 event-details">
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
          <div className="col-xs-4 event-count align-right">
            {team.apps.length}
          </div>
        </div>
      </li>
    );
  }

  renderUserDetails() {
    let showTest = true;
    if (!this.state.testResults ||
      this.state.testResults.error === true &&
      this.state.testResults.result === null) {
      showTest = false;
    }

    return (
      <div className="box dashboard-widget">
        <div className="box-header clearfix">
          <div className="row">
            <div className="col-xs-8">
              <h3>{i18n.t('Team')}</h3>
            </div>
            <div className="col-xs-4 align-right">{i18n.t('Apps')}</div>
          </div>
        </div>
        <div className="box-content">
          <div className="tab-pane active">
              {showTest &&
                <ul className="group-list group-list-small">
                  {this.state.testResults.result.teams.map((team) => {
                      return this.renderTeam(team);
                  })}
                </ul>
              }
              {!showTest &&
                <div className="group-list-empty">
                    <a className="btn btn-default btn-sm" onClick={this.testConfig}>
                      {i18n.t('Test')}
                    </a>
                </div>
              }
          </div>
        </div>
      </div>
    );
  }

  render() {
    let metadata = this.props.plugin.metadata;

    return (
      <div>
        <div className="ref-itunesconnect-settings">
          {this.props.children}
        </div>

        {this.state.testResults &&
          <div className="ref-itunesconnect-test-results">
            <h4>Test Results</h4>
            {this.state.testResults.error ?
              <div className="alert alert-block alert-error">
                {this.state.testResults.message}
              </div>
            :
              <div className="alert alert-block alert-success">
                {this.state.testResults.message}
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
