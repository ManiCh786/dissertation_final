"""Generate dissertation-ready Azure scalability table/chart/text from genuine run evidence.

The script intentionally fails if the three successful Azure runs are absent. This prevents
accidental creation of a dissertation performance section from local or placeholder timings.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from common import PROJECT_ROOT

TARGETS = [100_000, 500_000, 1_000_000]


def main() -> None:
    source = PROJECT_ROOT / 'azure_execution_evidence' / 'azure_scalability_results.csv'
    if not source.exists():
        raise SystemExit('No genuine Azure results found. Run src/12_run_azure_benchmark.py first.')
    df = pd.read_csv(source)
    df = df[df['status'].astype(str).str.lower().eq('succeeded')].copy()
    missing = [n for n in TARGETS if n not in set(df['sample_size'].astype(int))]
    if missing:
        raise SystemExit(f'Missing successful Azure results for: {missing}')
    df = df[df['sample_size'].isin(TARGETS)].sort_values('sample_size').drop_duplicates('sample_size', keep='last')

    out_dir = PROJECT_ROOT / 'azure_execution_evidence'
    table_cols = [
        'sample_size', 'adf_pipeline_seconds', 'adf_throughput_rows_per_sec',
        'databricks_activity_seconds', 'databricks_activity_throughput_rows_per_sec', 'adf_run_id'
    ]
    df[table_cols].to_csv(out_dir / 'chapter4_azure_scalability_table.csv', index=False)

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(df['sample_size'], df['adf_pipeline_seconds'], marker='o', label='ADF end-to-end pipeline')
    if df['databricks_activity_seconds'].notna().any():
        ax.plot(df['sample_size'], df['databricks_activity_seconds'], marker='o', label='Databricks activity')
    ax.set_xlabel('Input records')
    ax.set_ylabel('Execution time (seconds)')
    ax.set_title('Azure Pipeline Scalability Across Controlled Workloads')
    ax.grid(True, alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_dir / 'Figure_Azure_Scalability_100K_500K_1M.png', dpi=220)
    plt.close(fig)

    r = {int(row.sample_size): row for row in df.itertuples(index=False)}
    lines = [
        '# Generated Chapter 4 Azure Scalability Results',
        '',
        'The scalability experiment was executed in Microsoft Azure using controlled workloads of 100,000, 500,000 and 1,000,000 e-commerce event records. '
        f"The ADF pipeline completed the 100,000-record workload in {r[100000].adf_pipeline_seconds:.2f} seconds, the 500,000-record workload in {r[500000].adf_pipeline_seconds:.2f} seconds, and the 1,000,000-record workload in {r[1000000].adf_pipeline_seconds:.2f} seconds. "
        f"The corresponding end-to-end throughputs were {r[100000].adf_throughput_rows_per_sec:,.2f}, {r[500000].adf_throughput_rows_per_sec:,.2f}, and {r[1000000].adf_throughput_rows_per_sec:,.2f} records per second, respectively. "
        'Each measurement was derived from a successful Azure Data Factory run and retained with its run ID and activity-level execution evidence in the practical repository.',
        '',
        '## Evidence run IDs',
    ]
    for n in TARGETS:
        lines.append(f'- {n:,} records: `{r[n].adf_run_id}`')
    lines += [
        '',
        'The 1,920-record demonstration run was treated only as a functional sanity test and was not used as evidence of scalability. The scalability conclusion was based on the three controlled Azure workloads above.',
    ]
    (out_dir / 'chapter4_azure_results_generated.md').write_text('\n'.join(lines), encoding='utf-8')
    print('Generated dissertation-ready Azure table, figure and past-tense results text from genuine run evidence.')


if __name__ == '__main__':
    main()
