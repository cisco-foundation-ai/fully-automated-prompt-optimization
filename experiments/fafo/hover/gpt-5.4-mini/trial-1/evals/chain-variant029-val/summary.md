# Evaluation Summary

Total cases: 300

## Composite Score
- average: 72.33

## Score Breakdown
- num_found: 2.68
- num_gold: 3.00
- partial_recall: 89.22
- recall: 72.33

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.008 | 0.002 | 0.005 |
| summarize_hop1 | 2.373 | 2.112 | 3.643 |
| query_hop2 | 0.738 | 0.651 | 1.137 |
| retrieve_hop2 | 0.739 | 0.003 | 1.536 |
| summarize_hop2 | 3.080 | 2.792 | 5.257 |
| query_hop3 | 0.856 | 0.738 | 1.319 |
| retrieve_hop3 | 1.039 | 1.293 | 1.645 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **8.833** | **8.241** | **13.046** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 83 |
