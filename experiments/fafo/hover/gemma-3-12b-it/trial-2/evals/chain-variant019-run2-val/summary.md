# Evaluation Summary

Total cases: 300

## Composite Score
- average: 73.33

## Score Breakdown
- num_found: 2.70
- num_gold: 3.00
- num_missing: 0.30
- partial_recall: 90.11
- recall: 73.33

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.004 | 0.002 | 0.005 |
| summarize_hop1 | 3.300 | 2.693 | 7.021 |
| query_hop2 | 0.369 | 0.327 | 0.533 |
| retrieve_hop2 | 0.445 | 0.002 | 1.620 |
| summarize_hop2 | 7.173 | 6.146 | 9.919 |
| query_hop3 | 0.406 | 0.353 | 0.819 |
| retrieve_hop3 | 1.155 | 1.104 | 1.654 |
| summarize_hop3 | 8.548 | 6.878 | 12.073 |
| query_hop4 | 0.515 | 0.446 | 1.006 |
| retrieve_hop4 | 1.301 | 1.341 | 1.665 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **23.216** | **20.825** | **29.390** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop4 | 80 |
