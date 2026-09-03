# Azure Execution Evidence

This folder is the authoritative location for cloud execution evidence.

At package-preparation time, no Azure credentials were available, so no cloud timings were invented. `final_gate_status.txt` intentionally records that the final Azure evidence gate is not yet satisfied.

After authenticating to the real Azure environment, run:

```powershell
python src/12_run_azure_benchmark.py
```

Successful execution must create:

- `azure_scalability_results.csv` with successful 100K, 500K and 1M rows;
- `azure_run_<size>_<runid>.json` for each workload;
- actual ADF run IDs and activity timing evidence;
- Databricks notebook return output with raw/clean row counts and processing timing.

Then run:

```powershell
python src/15_generate_azure_results_artifacts.py
python src/11_validate_submission.py --require-azure
```

Only after the final gate passes should Azure execution times be reported in the dissertation.
