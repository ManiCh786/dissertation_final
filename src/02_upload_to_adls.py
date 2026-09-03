"""Prepared ADLS Gen2 upload component using Microsoft Entra authentication.

A successful run of this script is required before claiming an ADLS upload was executed.
"""
from pathlib import Path, PurePosixPath
import argparse
from azure.core.exceptions import ResourceExistsError
from azure.identity import DefaultAzureCredential
from azure.storage.filedatalake import DataLakeServiceClient
from common import require_env


def ensure_directory(fs_client, remote_dir: str):
    current = ''
    for part in PurePosixPath(remote_dir).parts:
        if part in ('/', '.', ''):
            continue
        current = f'{current}/{part}'.strip('/')
        directory = fs_client.get_directory_client(current)
        try:
            directory.create_directory()
        except ResourceExistsError:
            pass


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', required=True)
    parser.add_argument('--remote', required=True, help='Example: landing/ecommerce_100000.csv')
    args = parser.parse_args()

    source = Path(args.source)
    if not source.exists():
        raise SystemExit(f'Local file not found: {source}')

    account = require_env('AZURE_STORAGE_ACCOUNT')
    filesystem = require_env('ADLS_FILE_SYSTEM')
    account_url = f'https://{account}.dfs.core.windows.net'

    credential = DefaultAzureCredential(exclude_interactive_browser_credential=False)
    service = DataLakeServiceClient(account_url=account_url, credential=credential)

    try:
        fs = service.create_file_system(file_system=filesystem)
        print(f'Created file system: {filesystem}')
    except ResourceExistsError:
        fs = service.get_file_system_client(filesystem)

    remote = PurePosixPath(args.remote)
    remote_dir = str(remote.parent)
    if remote_dir not in ('', '.'):
        ensure_directory(fs, remote_dir)

    file_client = fs.get_file_client(str(remote))
    with source.open('rb') as fh:
        file_client.upload_data(fh, overwrite=True)

    props = file_client.get_file_properties()
    print('UPLOAD SUCCESS')
    print(f'Account : {account}')
    print(f'File system: {filesystem}')
    print(f'Remote path: {remote}')
    print(f'Size: {props.size:,} bytes')


if __name__ == '__main__':
    main()
