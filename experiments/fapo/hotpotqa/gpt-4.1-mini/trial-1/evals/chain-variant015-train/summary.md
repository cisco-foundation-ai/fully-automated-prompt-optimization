# Evaluation Summary

Total cases: 150

## Composite Score
- average: 74.00

## Score Breakdown
- exact_match: 74.00
- f1: 79.92

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.050 | 0.002 | 0.042 |
| summarize_hop1 | 3.724 | 3.280 | 6.655 |
| query_hop2 | 1.749 | 1.605 | 2.790 |
| retrieve_hop2 | 0.785 | 0.004 | 1.730 |
| summarize_hop2 | 4.236 | 3.639 | 7.314 |
| answer | 1.903 | 1.686 | 3.254 |
| **Total** | **12.447** | **11.352** | **19.598** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 39 |
