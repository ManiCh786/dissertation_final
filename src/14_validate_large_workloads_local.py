"""Run the full local ETL + Gold analytics on 100K/500K/1M controlled workloads.

This provides a reproducible large-workload FUNCTIONAL baseline. It is useful as a
sanity check before cloud execution but is never labelled as Azure performance evidence.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

import pandas as pd

from common import PROJECT_ROOT

DEFAULT_SIZES = (100_000, 500_000, 1_000_000)


def run(cmd: list[str]) -> float:
    start = time.perf_counter()
    subprocess.run(cmd, check=True, cwd=PROJECT_ROOT)
    return time.perf_counter() - start


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument('--sizes', nargs='*', type=int, default=list(DEFAULT_SIZES))
    args = p.parse_args()

    base_out = PROJECT_ROOT / 'outputs' / 'large_workload_validation'
    base_out.mkdir(parents=True, exist_ok=True)
    rows = []

    for size in args.sizes:
        source = PROJECT_ROOT / 'data' / 'samples' / f'ecommerce_{size}.csv'
        if not source.exists():
            raise SystemExit(f'Missing {source}. Run src/01_create_benchmark_workloads.py first.')
        run_dir = base_out / str(size)
        silver_dir = run_dir / 'silver'
        gold_dir = run_dir / 'gold'
        silver_dir.mkdir(parents=True, exist_ok=True)
        gold_dir.mkdir(parents=True, exist_ok=True)

        print(f'\n=== LOCAL LARGE-WORKLOAD VALIDATION {size:,} ===')
        etl_seconds = run([
            sys.executable, 'src/04_local_etl_pandas.py',
            '--input', str(source), '--output-dir', str(silver_dir)
        ])
        gold_seconds = run([
            sys.executable, 'src/05_create_gold_metrics.py',
            '--input', str(silver_dir / 'ecommerce_events_clean.csv'),
            '--output-dir', str(gold_dir)
        ])

        quality = pd.read_csv(silver_dir / 'data_quality_report.csv').set_index('metric')['value'].to_dict()
        kpi = pd.read_csv(gold_dir / 'gold_kpi_summary.csv').set_index('metric')['value'].to_dict()
        rows.append({
            'scope': 'LOCAL_FULL_PIPELINE_VALIDATION_NOT_AZURE',
            'sample_size': size,
            'raw_rows': int(quality['raw_rows']),
            'clean_rows': int(quality['clean_rows']),
            'removed_rows': int(quality['removed_rows']),
            'unique_users': int(float(kpi['unique_users'])),
            'unique_sessions': int(float(kpi['unique_sessions'])),
            'etl_seconds': round(etl_seconds, 4),
            'gold_seconds': round(gold_seconds, 4),
            'total_seconds': round(etl_seconds + gold_seconds, 4),
            'throughput_rows_per_sec': round(size / (etl_seconds + gold_seconds), 2),
        })

    summary = pd.DataFrame(rows)
    out_csv = base_out / 'large_workload_validation_NOT_AZURE.csv'
    summary.to_csv(out_csv, index=False)
    (base_out / 'README.txt').write_text(
        'These results are local Pandas functional/scalability baselines only. They prove the code handles 100K/500K/1M controlled workloads locally, but they are not ADF or Databricks cloud metrics.\n',
        encoding='utf-8'
    )
    print('\n' + summary.to_string(index=False))
    print(f'\nSaved: {out_csv}')
    print('IMPORTANT: NOT AZURE EVIDENCE. Replace/augment dissertation scalability results with genuine Azure run records from src/12_run_azure_benchmark.py.')


if __name__ == '__main__':
    main()
