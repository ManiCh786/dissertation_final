"""Prepared helper to upload local Gold CSVs to the designed ADLS gold/ layer.

Only describe the upload as executed when successful Azure output/evidence is retained.
"""
from pathlib import Path
import subprocess
import sys
from common import PROJECT_ROOT


def main():
    gold_dir = PROJECT_ROOT / 'data' / 'gold'
    files = sorted(gold_dir.glob('gold_*.csv'))
    if not files:
        raise SystemExit('No Gold CSV files found. Run 05_create_gold_metrics.py first.')
    uploader = Path(__file__).with_name('02_upload_to_adls.py')
    for file in files:
        remote = f'gold/{file.name}'
        subprocess.run([sys.executable, str(uploader), '--source', str(file), '--remote', remote], check=True)


if __name__ == '__main__':
    main()
