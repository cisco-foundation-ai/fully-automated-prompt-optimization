# Evaluation Summary

Total cases: 150

## Composite Score
- average: 73.33

## Score Breakdown
- exact_match: 73.33
- f1: 78.83

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.040 | 0.002 | 0.042 |
| summarize_hop1 | 3.623 | 3.024 | 6.878 |
| query_hop2 | 2.022 | 1.736 | 3.983 |
| retrieve_hop2 | 0.355 | 0.002 | 1.320 |
| summarize_hop2 | 2.954 | 2.660 | 5.052 |
| answer | 1.705 | 1.524 | 2.675 |
| **Total** | **10.698** | **10.031** | **16.308** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 40 |
