"""Create deterministic 100K/500K/1M benchmark workloads from the validated demo schema.

The purpose is workload scaling, not creation of new empirical customer behaviour.
Rows are repeated from the demonstration data while identifiers/timestamps are shifted per
replication block so that the benchmark files are not collapsed as duplicates. Existing
quality defects in the source demo (unsupported event, missing session, non-positive price,
and the intentional duplicate pair) remain represented and exercise the cleaning rules.

These files are suitable for controlled scalability benchmarking. They must be described as
*controlled benchmark workloads derived from the demonstration schema*, not as independent
real-world observations.
"""
from __future__ import annotations

import argparse
import hashlib
import math
from pathlib import Path

import pandas as pd

from common import PROJECT_ROOT

TARGETS = (100_000, 500_000, 1_000_000)
ID_COLUMNS = ("product_id", "category_id", "user_id")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _shift_numeric(series: pd.Series, offset: int) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce")
    shifted = numeric + offset
    # Preserve missing values and prefer integer rendering where possible.
    return shifted.astype("Int64")


def build_workload(base: pd.DataFrame, target: int) -> pd.DataFrame:
    if target <= 0:
        raise ValueError("target must be positive")
    blocks = math.ceil(target / len(base))
    frames = []
    for block in range(blocks):
        part = base.copy()
        # Offset timestamps by blocks to prevent cross-block exact duplicates.
        parsed = pd.to_datetime(part["event_time"], errors="coerce", utc=True)
        part["event_time"] = (parsed + pd.to_timedelta(block, unit="D")).dt.strftime("%Y-%m-%d %H:%M:%S UTC")

        # Shift numeric identifiers while preserving NaNs.
        for col, scale in (("product_id", 10_000_000), ("category_id", 10_000_000), ("user_id", 1_000_000)):
            part[col] = _shift_numeric(part[col], block * scale)

        # Keep missing sessions missing; suffix valid sessions so each block is distinct.
        session = part["user_session"]
        part["user_session"] = session.where(session.isna(), session.astype(str) + f"-b{block:04d}")
        frames.append(part)

    out = pd.concat(frames, ignore_index=True).iloc[:target].copy()
    assert len(out) == target
    return out


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--input", default=str(PROJECT_ROOT / "data" / "demo" / "demo_ecommerce_events.csv"))
    p.add_argument("--targets", nargs="*", type=int, default=list(TARGETS))
    p.add_argument("--output-dir", default=str(PROJECT_ROOT / "data" / "samples"))
    args = p.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        raise SystemExit(f"Input file not found: {input_path}")

    base = pd.read_csv(input_path)
    required = ["event_time", "event_type", "product_id", "category_id", "category_code", "brand", "price", "user_id", "user_session"]
    missing = [c for c in required if c not in base.columns]
    if missing:
        raise SystemExit(f"Input is missing required columns: {missing}")

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_rows = []

    print(f"Base workload: {input_path} ({len(base):,} rows)")
    for target in args.targets:
        df = build_workload(base, target)
        path = out_dir / f"ecommerce_{target}.csv"
        df.to_csv(path, index=False)
        manifest_rows.append({
            "sample_size": target,
            "file": path.name,
            "rows": len(df),
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
            "provenance": "controlled benchmark workload derived deterministically from demo_ecommerce_events.csv",
        })
        print(f"Created {path.name}: {len(df):,} rows, {path.stat().st_size / (1024**2):.2f} MiB")

    manifest = pd.DataFrame(manifest_rows)
    manifest_path = out_dir / "benchmark_workload_manifest.csv"
    manifest.to_csv(manifest_path, index=False)
    print(f"Manifest: {manifest_path}")
    print("IMPORTANT: workload scaling evidence only; do not describe these replicated rows as independent real-world observations.")


if __name__ == "__main__":
    main()
