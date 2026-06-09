# Evaluation Summary

Total cases: 300

## Composite Score
- average: 75.00

## Score Breakdown
- num_found: 2.72
- num_gold: 3.00
- num_missing: 0.28
- partial_recall: 90.56
- recall: 75.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.003 | 0.002 | 0.005 |
| summarize_hop1 | 6.343 | 5.636 | 8.632 |
| query_hop2 | 0.377 | 0.340 | 0.596 |
| retrieve_hop2 | 0.769 | 0.521 | 1.600 |
| summarize_hop2 | 7.320 | 6.248 | 11.357 |
| query_hop3 | 0.390 | 0.349 | 0.566 |
| retrieve_hop3 | 1.063 | 1.250 | 1.629 |
| summarize_hop3 | 8.791 | 7.564 | 14.289 |
| query_hop4 | 0.510 | 0.453 | 0.786 |
| retrieve_hop4 | 1.328 | 1.334 | 1.672 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **26.894** | **24.350** | **35.669** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop4 | 75 |
