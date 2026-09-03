"""Optional LOCAL baseline for generated workload files.

This script is part of the scalability-testing framework only. Any timings it
produces are local Pandas timings and MUST NOT be reported as Azure, ADF or
Databricks scalability results. The current practical package contains no
verified end-to-end Azure benchmark evidence for 100K/500K/1M workloads.
"""
from pathlib import Path
import time
import pandas as pd
from common import PROJECT_ROOT


def run_one(path: Path):
    t0 = time.perf_counter()
    df = pd.read_csv(path)
    df['event_time'] = pd.to_datetime(df['event_time'], errors='coerce', utc=True)
    df['event_type'] = df['event_type'].astype(str).str.lower().str.strip()
    df['price'] = pd.to_numeric(df['price'], errors='coerce')
    df = df.drop_duplicates()
    df = df[df['event_time'].notna()]
    df = df[df['event_type'].isin({'view', 'cart', 'remove_from_cart', 'purchase'})]
    df = df[df['product_id'].notna() & df['user_id'].notna() & df['user_session'].notna()]
    df = df[df['price'].gt(0)]
    _ = df.groupby('event_type').size()
    elapsed = time.perf_counter() - t0
    return len(df), elapsed


def main():
    sample_dir = PROJECT_ROOT / 'data' / 'samples'
    rows = []
    paths = sorted(sample_dir.glob('ecommerce_*.csv'), key=lambda p: int(p.stem.split('_')[-1]))
    for path in paths:
        n, sec = run_one(path)
        rows.append({
            'scope': 'LOCAL_PANDAS_BASELINE_NOT_AZURE',
            'file': path.name,
            'clean_rows': n,
            'processing_seconds': round(sec, 4),
            'throughput_rows_per_sec': round(n / sec, 2) if sec else None,
        })
    if not rows:
        raise SystemExit(
            'No sample files found. The scalability framework is present, but no local workload files are available. '
            'Run src/01_create_benchmark_workloads.py to create the controlled benchmark files.'
        )
    out = pd.DataFrame(rows)
    out_path = PROJECT_ROOT / 'outputs' / 'performance' / 'local_scalability_baseline_NOT_AZURE.csv'
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(out_path, index=False)
    print(out.to_string(index=False))
    print('Saved:', out_path)
    print('IMPORTANT: these are local Pandas timings and are not Azure scalability evidence.')


if __name__ == '__main__':
    main()
