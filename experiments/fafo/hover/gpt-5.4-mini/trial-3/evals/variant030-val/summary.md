# Evaluation Summary

Total cases: 300

## Composite Score
- average: 30.00

## Score Breakdown
- num_found: 2.04
- num_gold: 3.00
- num_missing: 0.96
- partial_recall: 68.00
- recall: 30.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.003 | 0.002 | 0.004 |
| summarize_hop1 | 5.501 | 5.119 | 8.361 |
| query_hop2 | 0.886 | 0.697 | 1.187 |
| retrieve_hop2 | 1.324 | 1.324 | 1.681 |
| summarize_hop2 | 2.438 | 2.225 | 3.856 |
| query_hop3 | 0.976 | 0.714 | 1.229 |
| retrieve_hop3 | 1.335 | 1.481 | 1.663 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **12.463** | **11.730** | **19.404** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 210 |
