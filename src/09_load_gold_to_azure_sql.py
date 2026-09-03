"""Prepared Azure SQL Gold-loader using passwordless Microsoft Entra authentication.

The local Gold CSVs are validated outputs, but their existence does not prove that
this Azure SQL loader was successfully executed.
"""
from pathlib import Path
import os
import pandas as pd
from dotenv import load_dotenv
from mssql_python import connect
from common import PROJECT_ROOT, require_env

TABLES = {
    'gold_customer_engagement.csv': ('customer_engagement', '''
        CREATE TABLE customer_engagement (
            user_id BIGINT NULL, views INT NULL, carts INT NULL, purchases INT NULL,
            remove_from_cart INT NULL, sessions INT NULL, purchase_value FLOAT NULL,
            total_interactions INT NULL, engagement_score FLOAT NULL, engagement_level VARCHAR(20) NULL
        )'''),
    'gold_conversion_funnel.csv': ('conversion_funnel', '''
        CREATE TABLE conversion_funnel (
            stage_order INT NULL, stage VARCHAR(50) NULL, sessions INT NULL,
            percent_of_view_sessions FLOAT NULL, conversion_from_previous_stage_pct FLOAT NULL
        )'''),
    'gold_cart_abandonment.csv': ('cart_abandonment', '''
        CREATE TABLE cart_abandonment (
            category_code VARCHAR(255) NULL, cart_sessions INT NULL,
            abandoned_sessions INT NULL, remove_from_cart_events INT NULL,
            abandonment_rate_pct FLOAT NULL
        )'''),
    'gold_category_performance.csv': ('category_performance', '''
        CREATE TABLE category_performance (
            category_code VARCHAR(255) NULL, views INT NULL, cart_additions INT NULL,
            purchases INT NULL, remove_from_cart_events INT NULL, purchase_revenue FLOAT NULL,
            view_to_cart_rate_pct FLOAT NULL, purchase_conversion_rate_pct FLOAT NULL
        )'''),
}


def sql_value(v):
    if pd.isna(v):
        return None
    if hasattr(v, 'item'):
        return v.item()
    return v


def main():
    conn_str = require_env('AZURE_SQL_CONNECTIONSTRING')
    gold_dir = PROJECT_ROOT / 'data' / 'gold'
    with connect(conn_str) as conn:
        cur = conn.cursor()
        for filename, (table, create_sql) in TABLES.items():
            path = gold_dir / filename
            if not path.exists():
                print(f'SKIP: {path} not found')
                continue
            df = pd.read_csv(path)
            cur.execute(f"IF OBJECT_ID('{table}', 'U') IS NOT NULL DROP TABLE {table};")
            cur.execute(create_sql)
            placeholders = ','.join(['?'] * len(df.columns))
            insert = f"INSERT INTO {table} ({','.join(df.columns)}) VALUES ({placeholders})"
            for row in df.itertuples(index=False, name=None):
                cur.execute(insert, tuple(sql_value(v) for v in row))
            conn.commit()
            print(f'Loaded {len(df):,} rows -> {table}')
    print('AZURE SQL LOAD COMPLETE')


if __name__ == '__main__':
    main()
