# Evaluation Summary

Total cases: 150

## Composite Score
- average: 70.00

## Score Breakdown
- num_found: 2.69
- num_gold: 3.00
- num_missing: 0.31
- partial_recall: 89.56
- recall: 70.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.028 | 0.004 | 0.014 |
| summarize_hop1 | 4.264 | 3.514 | 11.050 |
| query_hop2 | 0.352 | 0.292 | 0.662 |
| retrieve_hop2 | 0.442 | 0.004 | 1.615 |
| summarize_hop2 | 10.824 | 2.969 | 12.507 |
| query_hop3 | 0.377 | 0.287 | 1.263 |
| retrieve_hop3 | 0.697 | 0.010 | 1.640 |
| combine_retrievals | 0.005 | 0.005 | 0.009 |
| **Total** | **16.989** | **8.603** | **32.470** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3_trunc | 45 |
