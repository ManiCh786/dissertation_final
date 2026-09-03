"""Prepared Azure Data Factory trigger component via Azure Management SDK.

The local Pandas execution is not an ADF execution. A returned ADF run ID is required
before claiming this component was executed.
"""
import argparse
from azure.identity import DefaultAzureCredential
from azure.mgmt.datafactory import DataFactoryManagementClient
from common import require_env


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--sample-size', type=int, default=100000)
    a = p.parse_args()

    subscription_id = require_env('AZURE_SUBSCRIPTION_ID')
    resource_group = require_env('AZURE_RESOURCE_GROUP')
    factory_name = require_env('ADF_FACTORY_NAME')
    pipeline_name = require_env('ADF_PIPELINE_NAME')

    credential = DefaultAzureCredential(exclude_interactive_browser_credential=False)
    client = DataFactoryManagementClient(credential, subscription_id)

    params = {'sampleSize': a.sample_size}
    try:
        response = client.pipelines.create_run(resource_group, factory_name, pipeline_name, parameters=params)
    except Exception as exc:
        print('Pipeline could not be started with the sampleSize parameter.')
        print('If your ADF pipeline has no parameters, remove the parameter or run with a matching ADF parameter definition.')
        raise

    print('ADF PIPELINE STARTED')
    print('Run ID:', response.run_id)
    print('Save this run ID for script 08.')


if __name__ == '__main__':
    main()
