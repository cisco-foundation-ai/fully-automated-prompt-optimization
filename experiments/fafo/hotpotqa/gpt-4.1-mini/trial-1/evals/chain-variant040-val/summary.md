# Evaluation Summary

Total cases: 300

## Composite Score
- average: 68.33

## Score Breakdown
- exact_match: 68.33
- f1: 76.56

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.023 | 0.002 | 0.011 |
| summarize_hop1 | 4.053 | 3.421 | 7.803 |
| query_hop2 | 2.217 | 1.899 | 3.412 |
| retrieve_hop2 | 0.315 | 0.002 | 1.571 |
| summarize_hop2 | 3.148 | 2.863 | 5.292 |
| answer | 2.067 | 1.725 | 3.556 |
| **Total** | **11.823** | **10.815** | **18.011** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 95 |
