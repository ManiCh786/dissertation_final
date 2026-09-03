"""Execute and capture genuine Azure scalability evidence for 100K/500K/1M workloads.

This script performs three auditable steps for each workload:
1) uploads the benchmark CSV to ADLS Gen2 bronze/;
2) triggers the parameterised ADF pipeline;
3) waits for completion and records pipeline/activity timing plus Databricks notebook output.

It writes evidence ONLY from actual Azure SDK responses. If Azure authentication or a cloud
resource is unavailable, it fails instead of creating placeholder timings.
"""
from __future__ import annotations

import argparse
import csv
import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from azure.identity import DefaultAzureCredential
from azure.mgmt.datafactory import DataFactoryManagementClient
from azure.mgmt.datafactory.models import RunFilterParameters
from azure.storage.filedatalake import DataLakeServiceClient

from common import PROJECT_ROOT, require_env

TERMINAL = {"Succeeded", "Failed", "Cancelled"}
DEFAULT_SIZES = (100_000, 500_000, 1_000_000)


def iso(value: Any) -> str | None:
    return value.isoformat() if value else None


def upload_to_adls(credential, account: str, filesystem: str, local_path: Path, remote_path: str) -> dict:
    service = DataLakeServiceClient(
        account_url=f"https://{account}.dfs.core.windows.net",
        credential=credential,
    )
    fs = service.get_file_system_client(filesystem)
    file_client = fs.get_file_client(remote_path)
    with local_path.open("rb") as f:
        file_client.upload_data(f, overwrite=True)
    props = file_client.get_file_properties()
    return {
        "remote_path": remote_path,
        "uploaded_bytes": local_path.stat().st_size,
        "etag": str(props.etag),
        "last_modified": iso(props.last_modified),
    }


def activity_to_dict(activity) -> dict:
    output = activity.output if isinstance(activity.output, dict) else {}
    return {
        "activity_name": activity.activity_name,
        "activity_type": activity.activity_type,
        "status": activity.status,
        "start": iso(activity.activity_run_start),
        "end": iso(activity.activity_run_end),
        "duration_ms": activity.duration_in_ms,
        "run_output": output.get("runOutput"),
        "output": output,
        "error": activity.error,
    }


def wait_for_pipeline(client, rg: str, factory: str, run_id: str, poll_seconds: int, timeout_minutes: int):
    deadline = time.monotonic() + timeout_minutes * 60
    while True:
        run = client.pipeline_runs.get(rg, factory, run_id)
        print(f"  ADF {run_id}: {run.status}")
        if run.status in TERMINAL:
            return run
        if time.monotonic() >= deadline:
            raise TimeoutError(f"Timed out waiting for ADF run {run_id}")
        time.sleep(poll_seconds)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--sizes", nargs="*", type=int, default=list(DEFAULT_SIZES))
    p.add_argument("--poll-seconds", type=int, default=20)
    p.add_argument("--timeout-minutes", type=int, default=90)
    args = p.parse_args()

    subscription = require_env("AZURE_SUBSCRIPTION_ID")
    rg = require_env("AZURE_RESOURCE_GROUP")
    factory = require_env("ADF_FACTORY_NAME")
    pipeline = require_env("ADF_PIPELINE_NAME")
    storage = require_env("AZURE_STORAGE_ACCOUNT")
    filesystem = require_env("ADLS_FILE_SYSTEM")
    bronze_dir = require_env("ADLS_BRONZE_DIR")

    credential = DefaultAzureCredential(exclude_interactive_browser_credential=False)
    adf = DataFactoryManagementClient(credential, subscription)

    evidence_dir = PROJECT_ROOT / "azure_execution_evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    csv_path = evidence_dir / "azure_scalability_results.csv"
    all_rows = []

    for size in args.sizes:
        local_path = PROJECT_ROOT / "data" / "samples" / f"ecommerce_{size}.csv"
        if not local_path.exists():
            raise SystemExit(f"Missing benchmark workload: {local_path}. Run src/01_create_benchmark_workloads.py first.")

        remote = f"{bronze_dir}/ecommerce_{size}.csv"
        print(f"\n=== Azure benchmark: {size:,} rows ===")
        upload = upload_to_adls(credential, storage, filesystem, local_path, remote)
        print(f"  Uploaded to abfss://{filesystem}@{storage}.dfs.core.windows.net/{remote}")

        parameters = {
            "sampleSize": str(size),
            "inputFile": f"ecommerce_{size}.csv",
            "storageAccount": storage,
            "fileSystem": filesystem,
        }
        response = adf.pipelines.create_run(rg, factory, pipeline, parameters=parameters)
        run = wait_for_pipeline(adf, rg, factory, response.run_id, args.poll_seconds, args.timeout_minutes)

        if run.status != "Succeeded":
            raw_failure = {
                "sample_size": size,
                "upload": upload,
                "adf_run_id": run.run_id,
                "status": run.status,
                "message": run.message,
                "parameters": run.parameters,
            }
            fail_path = evidence_dir / f"azure_run_{size}_{run.run_id}_FAILED.json"
            fail_path.write_text(json.dumps(raw_failure, indent=2, default=str), encoding="utf-8")
            raise RuntimeError(f"ADF run failed for {size:,} rows. Evidence saved to {fail_path}")

        after = (run.run_start or datetime.now(timezone.utc)) - timedelta(hours=1)
        before = (run.run_end or datetime.now(timezone.utc)) + timedelta(hours=1)
        activities = adf.activity_runs.query_by_pipeline_run(
            rg,
            factory,
            run.run_id,
            RunFilterParameters(last_updated_after=after, last_updated_before=before),
        ).value
        activity_dicts = [activity_to_dict(a) for a in activities]
        databricks = next((a for a in activity_dicts if "databricks" in (a["activity_type"] or "").lower() or "notebook" in (a["activity_name"] or "").lower()), None)

        pipeline_seconds = (run.duration_in_ms / 1000.0) if run.duration_in_ms is not None else None
        db_seconds = (databricks["duration_ms"] / 1000.0) if databricks and databricks.get("duration_ms") is not None else None
        result = {
            "sample_size": size,
            "source_file": local_path.name,
            "adls_remote_path": upload["remote_path"],
            "adf_run_id": run.run_id,
            "status": run.status,
            "run_start_utc": iso(run.run_start),
            "run_end_utc": iso(run.run_end),
            "adf_pipeline_seconds": pipeline_seconds,
            "adf_throughput_rows_per_sec": round(size / pipeline_seconds, 2) if pipeline_seconds else None,
            "databricks_activity_seconds": db_seconds,
            "databricks_activity_throughput_rows_per_sec": round(size / db_seconds, 2) if db_seconds else None,
            "databricks_run_output": databricks.get("run_output") if databricks else None,
            "evidence_file": f"azure_run_{size}_{run.run_id}.json",
        }
        all_rows.append(result)

        evidence = {
            "scope": "GENUINE_AZURE_EXECUTION_EVIDENCE",
            "captured_at_utc": datetime.now(timezone.utc).isoformat(),
            "upload": upload,
            "pipeline": {
                "pipeline_name": run.pipeline_name,
                "run_id": run.run_id,
                "status": run.status,
                "run_start": iso(run.run_start),
                "run_end": iso(run.run_end),
                "duration_in_ms": run.duration_in_ms,
                "parameters": run.parameters,
            },
            "activities": activity_dicts,
            "summary": result,
        }
        evidence_path = evidence_dir / result["evidence_file"]
        evidence_path.write_text(json.dumps(evidence, indent=2, default=str), encoding="utf-8")
        print(f"  Succeeded. Pipeline: {pipeline_seconds:.2f}s" if pipeline_seconds is not None else "  Succeeded.")
        print(f"  Evidence: {evidence_path}")

    # Replace the summary with the complete latest benchmark suite to avoid stale mixed runs.
    fieldnames = list(all_rows[0].keys()) if all_rows else []
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)
    print(f"\nAzure scalability summary: {csv_path}")
    print("These timings came from Azure SDK run records and may be reported as Azure evidence.")


if __name__ == "__main__":
    main()
