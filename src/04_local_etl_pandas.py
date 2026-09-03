"""Validated local Pandas ETL used for the dissertation's demonstrated execution.

This script is the source of the evidenced 1,920 -> 1,916 functional test.
It does NOT represent an Azure Data Factory or Azure Databricks execution.
"""
from pathlib import Path
import argparse
import pandas as pd
from common import PROJECT_ROOT

VALID_EVENTS = {'view', 'cart', 'remove_from_cart', 'purchase'}
REQUIRED_COLUMNS = [
    'event_time', 'event_type', 'product_id', 'category_id',
    'category_code', 'brand', 'price', 'user_id', 'user_session'
]


def clean_with_audit(df: pd.DataFrame):
    """Return cleaned Silver data, a quality summary, and rejected-row evidence.

    Rejection rules are applied sequentially so each removed row receives one
    primary reason. This makes the 1,920 -> 1,916 result directly traceable.
    """
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f'Missing required columns: {missing}')

    work = df.copy()
    work.insert(0, 'source_row_number', range(2, len(work) + 2))  # CSV header is row 1
    work['_rejection_reason'] = pd.NA

    # 1) Exact duplicate rows: keep first occurrence, reject subsequent copies.
    duplicate_mask = work.drop(columns=['source_row_number', '_rejection_reason']).duplicated(keep='first')
    work.loc[duplicate_mask, '_rejection_reason'] = 'duplicate_record'

    # Normalise fields used by later validation rules.
    parsed_time = pd.to_datetime(work['event_time'], errors='coerce', utc=True)
    normalised_event = work['event_type'].astype(str).str.lower().str.strip()
    numeric_price = pd.to_numeric(work['price'], errors='coerce')

    active = work['_rejection_reason'].isna()
    mask = active & parsed_time.isna()
    work.loc[mask, '_rejection_reason'] = 'invalid_event_time'

    active = work['_rejection_reason'].isna()
    mask = active & ~normalised_event.isin(VALID_EVENTS)
    work.loc[mask, '_rejection_reason'] = 'unsupported_event_type'

    active = work['_rejection_reason'].isna()
    mask = active & (
        work['product_id'].isna() |
        work['user_id'].isna() |
        work['user_session'].isna()
    )
    work.loc[mask, '_rejection_reason'] = 'missing_required_identifier'

    active = work['_rejection_reason'].isna()
    mask = active & numeric_price.isna()
    work.loc[mask, '_rejection_reason'] = 'invalid_price'

    active = work['_rejection_reason'].isna()
    mask = active & numeric_price.le(0)
    work.loc[mask, '_rejection_reason'] = 'nonpositive_price'

    rejected = work[work['_rejection_reason'].notna()].copy()
    clean = work[work['_rejection_reason'].isna()].copy()

    # Apply the normalised values only to accepted rows.
    clean['event_time'] = pd.to_datetime(clean['event_time'], errors='coerce', utc=True)
    clean['event_type'] = clean['event_type'].astype(str).str.lower().str.strip()
    clean['price'] = pd.to_numeric(clean['price'], errors='coerce')
    clean['brand'] = clean['brand'].fillna('unknown').astype(str)
    clean['category_code'] = clean['category_code'].fillna('unknown').astype(str)
    clean['event_date'] = clean['event_time'].dt.date.astype(str)
    clean['event_hour'] = clean['event_time'].dt.hour
    clean['event_day'] = clean['event_time'].dt.day_name()
    clean['event_month'] = clean['event_time'].dt.strftime('%Y-%m')
    clean = clean.drop(columns=['source_row_number', '_rejection_reason'])

    reason_counts = rejected['_rejection_reason'].value_counts().to_dict()
    report_rows = [
        {'metric': 'raw_rows', 'value': int(len(df))},
        {'metric': 'duplicate_rows_removed', 'value': int(reason_counts.get('duplicate_record', 0))},
        {'metric': 'unsupported_event_type_rows_removed', 'value': int(reason_counts.get('unsupported_event_type', 0))},
        {'metric': 'invalid_event_time_rows_removed', 'value': int(reason_counts.get('invalid_event_time', 0))},
        {'metric': 'missing_required_identifier_rows_removed', 'value': int(reason_counts.get('missing_required_identifier', 0))},
        {'metric': 'invalid_price_rows_removed', 'value': int(reason_counts.get('invalid_price', 0))},
        {'metric': 'nonpositive_price_rows_removed', 'value': int(reason_counts.get('nonpositive_price', 0))},
        {'metric': 'clean_rows', 'value': int(len(clean))},
        {'metric': 'removed_rows', 'value': int(len(df) - len(clean))},
    ]
    report = pd.DataFrame(report_rows)

    rejected = rejected.drop(columns=['_rejection_reason']).join(
        work.loc[rejected.index, '_rejection_reason'].rename('rejection_reason')
    )
    return clean, report, rejected


def clean(df: pd.DataFrame) -> pd.DataFrame:
    """Compatibility helper returning only the cleaned DataFrame."""
    clean_df, _, _ = clean_with_audit(df)
    return clean_df


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--input', required=True)
    p.add_argument('--output-dir', default=str(PROJECT_ROOT / 'data' / 'silver'))
    a = p.parse_args()
    source = Path(a.input)
    if not source.exists():
        raise SystemExit(f'Input file not found: {source}')

    df = pd.read_csv(source)
    clean_df, report, rejected = clean_with_audit(df)

    out_dir = Path(a.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    clean_path = out_dir / 'ecommerce_events_clean.csv'
    report_path = out_dir / 'data_quality_report.csv'
    rejected_path = out_dir / 'data_quality_rejected_records.csv'

    clean_df.to_csv(clean_path, index=False)
    report.to_csv(report_path, index=False)
    rejected.to_csv(rejected_path, index=False)

    print('LOCAL PANDAS ETL - VALIDATED EXECUTION')
    print(report.to_string(index=False))
    print('\nRejected-row reasons:')
    if rejected.empty:
        print('  None')
    else:
        preview = rejected[['source_row_number', 'event_type', 'price', 'user_session', 'rejection_reason']].head(20)
        print(preview.to_string(index=False))
        if len(rejected) > len(preview):
            print(f'  ... {len(rejected) - len(preview):,} additional rejected rows retained in the audit CSV')
    print(f'\nSilver clean data: {clean_path}')
    print(f'Data-quality report: {report_path}')
    print(f'Rejected-row audit: {rejected_path}')
    print('Scope note: these are local Pandas results, not ADF/Databricks execution evidence.')


if __name__ == '__main__':
    main()
