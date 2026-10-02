# Evaluation Summary

Total cases: 150

## Composite Score
- average: 72.00

## Score Breakdown
- exact_match: 72.00
- f1: 78.38

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.073 | 0.002 | 0.036 |
| summarize_hop1 | 2.174 | 2.033 | 3.444 |
| query_hop2 | 1.186 | 1.088 | 2.077 |
| retrieve_hop2 | 0.606 | 0.003 | 1.705 |
| summarize_hop2 | 1.740 | 1.667 | 2.688 |
| answer | 0.951 | 0.810 | 1.369 |
| **Total** | **6.730** | **6.095** | **10.314** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 42 |
