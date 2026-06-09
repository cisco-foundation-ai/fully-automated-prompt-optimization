# Evaluation Summary

Total cases: 150

## Composite Score
- average: 70.00

## Score Breakdown
- exact_match: 70.00
- f1: 75.88

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.029 | 0.002 | 0.020 |
| summarize_hop1 | 2.866 | 2.427 | 5.159 |
| query_hop2 | 1.934 | 1.742 | 3.135 |
| retrieve_hop2 | 0.703 | 0.079 | 1.706 |
| summarize_hop2 | 2.298 | 2.171 | 3.823 |
| answer | 1.163 | 1.099 | 1.678 |
| **Total** | **8.993** | **8.250** | **16.385** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 45 |
