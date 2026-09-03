"""Validate the practical evidence before dissertation submission.

Default mode validates the local functional package and benchmark-workload preparation.
Use --require-azure for the FINAL submission gate. That mode fails unless genuine successful
Azure run evidence exists for 100K, 500K and 1M workloads.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from common import PROJECT_ROOT

EXPECTED_REMOVALS = {
    'duplicate_rows_removed': 1,
    'unsupported_event_type_rows_removed': 1,
    'missing_required_identifier_rows_removed': 1,
    'nonpositive_price_rows_removed': 1,
}
TARGET_SIZES = [100_000, 500_000, 1_000_000]


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument('--require-azure', action='store_true', help='Fail unless genuine Azure evidence for 100K/500K/1M exists.')
    args = p.parse_args()

    errors = []

    # Small functional/unit-test evidence.
    qpath = PROJECT_ROOT / 'data/silver/data_quality_report.csv'
    rpath = PROJECT_ROOT / 'data/silver/data_quality_rejected_records.csv'
    if not qpath.exists(): errors.append(f'Missing {qpath}')
    if not rpath.exists(): errors.append(f'Missing {rpath}')
    if not errors:
        q = pd.read_csv(qpath).set_index('metric')['value'].to_dict()
        if int(q.get('raw_rows', -1)) != 1920: errors.append('functional-test raw_rows is not 1920')
        if int(q.get('clean_rows', -1)) != 1916: errors.append('functional-test clean_rows is not 1916')
        if int(q.get('removed_rows', -1)) != 4: errors.append('functional-test removed_rows is not 4')
        for metric, expected in EXPECTED_REMOVALS.items():
            if int(q.get(metric, -1)) != expected: errors.append(f'{metric} is not {expected}')
        rejected = pd.read_csv(rpath)
        if len(rejected) != 4: errors.append('functional-test rejection audit does not contain exactly 4 rows')

    required_gold = [
        'gold_customer_engagement.csv', 'gold_conversion_funnel.csv', 'gold_cart_abandonment.csv',
        'gold_category_performance.csv', 'gold_kpi_summary.csv', 'gold_metric_definitions.csv'
    ]
    for f in required_gold:
        if not (PROJECT_ROOT / 'data/gold' / f).exists(): errors.append(f'Missing Gold output: {f}')

    vis = list((PROJECT_ROOT / 'visualizations_results').glob('*.png'))
    if len(vis) < 15: errors.append(f'Expected at least 15 PNG visualizations; found {len(vis)}')

    # Controlled benchmark workload evidence.
    manifest_path = PROJECT_ROOT / 'data/samples/benchmark_workload_manifest.csv'
    if not manifest_path.exists():
        errors.append('Missing benchmark_workload_manifest.csv')
    else:
        manifest = pd.read_csv(manifest_path)
        for size in TARGET_SIZES:
            sample = PROJECT_ROOT / 'data/samples' / f'ecommerce_{size}.csv'
            if not sample.exists():
                errors.append(f'Missing benchmark workload {sample.name}')
            else:
                # Count rows without loading the entire file into memory.
                with sample.open('rb') as f:
                    rows = sum(1 for _ in f) - 1
                if rows != size:
                    errors.append(f'{sample.name} contains {rows:,} data rows, expected {size:,}')

    local_perf = PROJECT_ROOT / 'outputs/performance/local_scalability_baseline_NOT_AZURE.csv'
    if not local_perf.exists():
        errors.append('Missing local scalability baseline (clearly labelled NOT_AZURE)')

    # Final cloud evidence gate.
    azure_summary = PROJECT_ROOT / 'azure_execution_evidence/azure_scalability_results.csv'
    if args.require_azure:
        if not azure_summary.exists():
            errors.append('FINAL GATE: missing genuine Azure scalability results. Run src/12_run_azure_benchmark.py after Azure authentication.')
        else:
            az = pd.read_csv(azure_summary)
            if 'status' not in az.columns or 'sample_size' not in az.columns:
                errors.append('FINAL GATE: Azure scalability summary has invalid columns.')
            else:
                for size in TARGET_SIZES:
                    row = az[(az['sample_size'] == size) & (az['status'].astype(str).str.lower() == 'succeeded')]
                    if row.empty:
                        errors.append(f'FINAL GATE: no successful Azure result for {size:,} rows.')
                    else:
                        evidence_file = row.iloc[0].get('evidence_file')
                        if not evidence_file or not (PROJECT_ROOT / 'azure_execution_evidence' / str(evidence_file)).exists():
                            errors.append(f'FINAL GATE: missing JSON run evidence for {size:,} rows.')

    if errors:
        print('SUBMISSION VALIDATION FAILED')
        for e in errors:
            print(' -', e)
        raise SystemExit(1)

    print('SUBMISSION VALIDATION PASSED')
    print(' - 1,920-row functional sanity test is traceable (1,916 clean, 4 rejected)')
    print(' - Gold analytics and 15 local analytical figures are present')
    print(' - controlled 100K/500K/1M benchmark workloads are present with manifest')
    print(' - local performance results are explicitly labelled NOT_AZURE')
    if args.require_azure:
        print(' - FINAL GATE PASSED: genuine successful Azure evidence exists for 100K/500K/1M')
    else:
        print(' - Azure final gate was not requested; run with --require-azure before final dissertation submission')


if __name__ == '__main__':
    main()
