# Evaluation Summary

Total cases: 300

## Composite Score
- average: 66.33

## Score Breakdown
- exact_match: 66.33
- f1: 74.45

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.003 | 0.003 | 0.005 |
| summarize_hop1 | 6.109 | 5.075 | 11.919 |
| query_hop2 | 2.337 | 2.137 | 3.889 |
| retrieve_hop2 | 0.494 | 0.096 | 1.523 |
| summarize_hop2 | 4.393 | 3.966 | 7.397 |
| answer | 2.095 | 1.859 | 3.338 |
| **Total** | **15.431** | **14.178** | **26.661** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 101 |
