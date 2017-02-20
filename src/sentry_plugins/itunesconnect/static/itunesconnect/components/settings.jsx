import React from 'react';
import {i18n, IndicatorStore, LoadingError, LoadingIndicator, plugins} from 'sentry';

class Settings extends plugins.BasePlugin.DefaultSettings {
  constructor(props) {
    super(props);
  }

  fetchData() {
    super.fetchData();

    // this.api.request(`${this.getPluginEndpoint()}tenants/`, {
    //   success: (data) => {
    //     this.setState({
    //       tenants: data,
    //       tenantsLoading: false,
    //       tenantsError: false,
    //     });
    //   },
    //   error: (error) => {
    //     this.setState({
    //       tenantsLoading: false,
    //       tenantsError: true,
    //     });
    //   }
    // });
  }

  render() {
    let metadata = this.props.plugin.metadata;

    let url = ('/plugins/itunesconnect/start/' + this.props.organization.slug +
               '/' + this.props.project.slug)
    return (
      <div>
        <div className="ref-itunesconnect-settings">
          {this.props.children}
        </div>
        {this.state.testResults &&
          <div className="ref-itunesconnect-test-results">
            <h4>Test Results</h4>
            {this.state.testResults.error ?
              <div className="alert alert-block alert-error">{this.state.testResults.message}</div>
            :
              <div className="alert alert-block alert-success">{this.state.testResults.message}</div>
            }
          </div>
        }
      </div>
    );
  }
}

export default Settings;
