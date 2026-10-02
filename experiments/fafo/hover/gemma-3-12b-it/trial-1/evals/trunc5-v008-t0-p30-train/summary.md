# Evaluation Summary

Total cases: 150

## Composite Score
- average: 74.00

## Score Breakdown
- num_found: 2.73
- num_gold: 3.00
- num_missing: 0.27
- partial_recall: 91.11
- recall: 74.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.014 | 0.004 | 0.073 |
| summarize_hop1 | 2.594 | 1.991 | 6.365 |
| query_hop2 | 0.321 | 0.284 | 0.457 |
| retrieve_hop2 | 1.430 | 1.343 | 1.666 |
| summarize_hop2 | 1.984 | 1.640 | 4.344 |
| query_hop3 | 0.320 | 0.276 | 0.704 |
| retrieve_hop3 | 1.113 | 1.321 | 1.621 |
| summarize_hop3 | 1.938 | 1.500 | 4.592 |
| query_hop4 | 0.302 | 0.277 | 0.437 |
| retrieve_hop4 | 0.953 | 1.280 | 1.617 |
| summarize_hop4 | 1.887 | 1.549 | 3.648 |
| query_hop5 | 0.298 | 0.275 | 0.397 |
| retrieve_hop5 | 0.774 | 1.047 | 1.614 |
| combine_retrievals | 0.009 | 0.009 | 0.014 |
| **Total** | **13.939** | **12.805** | **24.119** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop5_trunc | 39 |
