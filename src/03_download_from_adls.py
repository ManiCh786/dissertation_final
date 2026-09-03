"""Prepared ADLS Gen2 download/verification component.

Code availability alone is not evidence that Azure access was successfully tested.
"""
from pathlib import Path
import argparse
from azure.identity import DefaultAzureCredential
from azure.storage.filedatalake import DataLakeServiceClient
from common import require_env, ensure_parent


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--remote', required=True)
    p.add_argument('--output', required=True)
    a = p.parse_args()

    account = require_env('AZURE_STORAGE_ACCOUNT')
    filesystem = require_env('ADLS_FILE_SYSTEM')
    service = DataLakeServiceClient(
        account_url=f'https://{account}.dfs.core.windows.net',
        credential=DefaultAzureCredential(exclude_interactive_browser_credential=False),
    )
    fs = service.get_file_system_client(filesystem)
    data = fs.get_file_client(a.remote).download_file().readall()
    out = ensure_parent(Path(a.output))
    out.write_bytes(data)
    print(f'DOWNLOAD SUCCESS: {a.remote} -> {out} ({len(data):,} bytes)')


if __name__ == '__main__':
    main()
