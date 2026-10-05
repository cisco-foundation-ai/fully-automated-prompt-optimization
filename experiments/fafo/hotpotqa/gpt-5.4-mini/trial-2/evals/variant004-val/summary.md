# Evaluation Summary

Total cases: 300

## Composite Score
- average: 69.00

## Score Breakdown
- exact_match: 69.00
- f1: 75.15

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.022 | 0.002 | 0.009 |
| summarize_hop1 | 1.710 | 1.474 | 2.587 |
| query_hop2 | 1.090 | 1.031 | 1.579 |
| retrieve_hop2 | 1.337 | 1.337 | 1.678 |
| summarize_hop2 | 1.131 | 1.038 | 1.653 |
| answer | 0.902 | 0.805 | 1.235 |
| **Total** | **6.193** | **5.744** | **8.349** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 93 |
