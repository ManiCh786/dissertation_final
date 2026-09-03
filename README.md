# Azure E-Commerce Behavioural Data Engineering Practical - Supervisor Feedback Resolved

**Dissertation topic:** Design and Implementation of a Scalable Azure-Based Data Engineering Pipeline for E-Commerce Behavioural Data Analytics and Visualisation

## What changed after the final supervisor review

This version corrects the practical design around the two dataset scales that must not be confused:

1. **Functional sanity test:** 1,920 raw records -> 1,916 clean records. This validates the cleaning and Gold-layer analytical logic only.
2. **Scalability experiment:** controlled workloads of **100,000, 500,000 and 1,000,000 records**, with a cloud execution workflow that records actual ADLS/ADF/Databricks evidence.

The practical now includes a final validation gate that will **fail** if the dissertation keeps the Azure scalability claim but genuine successful Azure evidence for all three workloads is missing.

## Current evidence status

### Executed and retained in this package

- Local Pandas functional sanity test: 1,920 raw -> 1,916 clean; 4 traceable rejected rows.
- Local Gold analytics: engagement, ordered session funnel, cart abandonment, category performance, KPI summary and metric definitions.
- Fifteen analytical figures generated from validated local Silver/Gold outputs.
- Deterministic controlled benchmark files at exactly 100K, 500K and 1M rows.
- Benchmark file manifest with exact row counts, file sizes and SHA-256 hashes.
- Local lightweight scalability baseline for all three workloads, explicitly labelled **NOT_AZURE**.

### Prepared for genuine Azure execution

Target route:

`Controlled workload -> ADLS Gen2 bronze -> ADF -> Azure Databricks/PySpark -> ADLS Silver/Gold -> Azure SQL -> Power BI`

The following are included:

- parameterised Databricks notebook;
- parameterised ADF pipeline template;
- ADLS upload/authentication helpers;
- automated ADF trigger/monitor/evidence collector;
- Azure SQL evidence capture;
- automatic Chapter 4 scalability table/figure/text generator from genuine Azure run records.

**No Azure credentials were available in the environment used to prepare this package, so Azure execution times were not fabricated.** Run the cloud workflow in the authenticated student Azure account before final submission if the title/Objectives/RQs continue to claim Azure scalability evaluation.

## The final practical workflow

### A. Reproduce the 1,920-row sanity test

```powershell
python src/04_local_etl_pandas.py --input data/demo/demo_ecommerce_events.csv
python src/05_create_gold_metrics.py --input data/silver/ecommerce_events_clean.csv
python src/visualizations.py
```

Expected result: 1,920 raw, 1,916 clean, four rejected rows, six Gold evidence tables, 15 PNG figures.

### B. Recreate the required scalability workloads

```powershell
python src/01_create_benchmark_workloads.py
```

This generates:

- `data/samples/ecommerce_100000.csv`
- `data/samples/ecommerce_500000.csv`
- `data/samples/ecommerce_1000000.csv`
- `data/samples/benchmark_workload_manifest.csv`

The workloads are controlled workload-scale data derived deterministically from the demonstration event schema. They must not be described as one million independent real-world customer observations.

### C. Optional local pre-cloud baseline

```powershell
python src/10_scalability_test_local.py
```

Output: `outputs/performance/local_scalability_baseline_NOT_AZURE.csv`.

These timings are for local Pandas only and must never be inserted into a table labelled Azure/ADF/Databricks performance.

### D. Execute the real Azure benchmark

Complete `docs/AZURE_EXECUTION_CHECKLIST.md`, then run:

```powershell
python src/00_validate_azure_login.py
python src/12_run_azure_benchmark.py
```

A successful run creates:

- `azure_execution_evidence/azure_scalability_results.csv`
- one JSON evidence record for each ADF run, containing run ID, timestamps, duration, activity run details and Databricks notebook output.

Microsoft's current ADF/Databricks pattern supports notebook `baseParameters`, and the Databricks notebook reads the task parameters through `dbutils.widgets`. The code in this package follows that parameterised pattern.

### E. Generate dissertation-ready scalability evidence

After all three Azure runs succeed:

```powershell
python src/15_generate_azure_results_artifacts.py
```

This produces:

- `chapter4_azure_scalability_table.csv`
- `Figure_Azure_Scalability_100K_500K_1M.png`
- `chapter4_azure_results_generated.md`

The results paragraph is written in past tense from retained Azure timings and run IDs.

### F. Final submission gate

```powershell
python src/11_validate_submission.py --require-azure
```

If this command fails, do not submit the dissertation with Objective/RQ 5 claiming that Azure scalability was empirically evaluated.

## Key feedback-resolution documents

- `docs/SUPERVISOR_FEEDBACK_RESOLUTION.md`
- `docs/IMPLEMENTATION_STATUS.md`
- `docs/AZURE_EXECUTION_CHECKLIST.md`
- `docs/FIGURE_EVIDENCE_PLAN.md`
- `docs/DISSERTATION_ALIGNMENT_NOTES.md`

## Security

The project uses `DefaultAzureCredential`/Microsoft Entra patterns. Do not place storage keys, SAS tokens, Azure SQL passwords, client secrets or Databricks PATs in the dissertation repository.
