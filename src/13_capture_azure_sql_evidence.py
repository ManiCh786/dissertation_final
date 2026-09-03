"""Capture genuine Azure SQL Gold-table row counts as submission evidence."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from mssql_python import connect

from common import PROJECT_ROOT, require_env

TABLES = ["customer_engagement", "conversion_funnel", "cart_abandonment", "category_performance"]


def main() -> None:
    conn_str = require_env("AZURE_SQL_CONNECTIONSTRING")
    rows = []
    with connect(conn_str) as conn:
        cur = conn.cursor()
        for table in TABLES:
            cur.execute(f"SELECT COUNT(*) FROM dbo.{table}")
            count = int(cur.fetchone()[0])
            rows.append({"table": f"dbo.{table}", "row_count": count})
            print(f"dbo.{table}: {count:,} rows")

    evidence = {
        "scope": "GENUINE_AZURE_SQL_EXECUTION_EVIDENCE",
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "tables": rows,
    }
    out = PROJECT_ROOT / "azure_execution_evidence" / "azure_sql_table_counts.json"
    out.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    print(f"Saved: {out}")


if __name__ == "__main__":
    main()
