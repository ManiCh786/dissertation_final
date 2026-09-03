"""Prepared helper to retrieve status/duration for a real ADF pipeline run.

Use only with an actual run ID; do not infer ADF timings from local execution.
"""
import argparse
from datetime import timezone
from azure.identity import DefaultAzureCredential
from azure.mgmt.datafactory import DataFactoryManagementClient
from common import require_env


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--run-id', required=True)
    a = p.parse_args()

    client = DataFactoryManagementClient(
        DefaultAzureCredential(exclude_interactive_browser_credential=False),
        require_env('AZURE_SUBSCRIPTION_ID')
    )
    run = client.pipeline_runs.get(require_env('AZURE_RESOURCE_GROUP'), require_env('ADF_FACTORY_NAME'), a.run_id)
    print('Run ID:', run.run_id)
    print('Status:', run.status)
    print('Start:', run.run_start)
    print('End:', run.run_end)
    if run.run_start and run.run_end:
        duration = (run.run_end - run.run_start).total_seconds()
        print(f'Duration: {duration:.2f} seconds')


if __name__ == '__main__':
    main()
