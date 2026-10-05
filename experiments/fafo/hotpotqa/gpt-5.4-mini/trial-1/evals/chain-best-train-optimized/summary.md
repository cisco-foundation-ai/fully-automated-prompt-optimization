# Evaluation Summary

Total cases: 150

## Composite Score
- average: 71.33

## Score Breakdown
- exact_match: 71.33
- f1: 78.73

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.235 | 0.002 | 2.590 |
| summarize_hop1 | 1.429 | 1.226 | 2.065 |
| query_hop2 | 1.092 | 1.026 | 1.510 |
| retrieve_hop2 | 0.965 | 0.005 | 4.394 |
| summarize_hop2 | 1.430 | 1.348 | 1.967 |
| answer | 0.855 | 0.748 | 1.266 |
| **Total** | **6.006** | **4.989** | **14.033** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 43 |
