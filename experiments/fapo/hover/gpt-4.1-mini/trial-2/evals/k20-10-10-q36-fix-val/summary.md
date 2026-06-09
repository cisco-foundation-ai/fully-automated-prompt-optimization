# Evaluation Summary

Total cases: 300

## Composite Score
- average: 65.67

## Score Breakdown
- num_found: 2.61
- num_gold: 3.00
- partial_recall: 86.89
- recall: 65.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.020 | 0.002 | 0.006 |
| summarize_hop1 | 4.366 | 3.762 | 7.926 |
| query_hop2 | 0.800 | 0.585 | 1.735 |
| retrieve_hop2 | 0.354 | 0.002 | 1.522 |
| summarize_hop2 | 4.757 | 3.954 | 9.342 |
| query_hop3 | 0.851 | 0.592 | 1.717 |
| retrieve_hop3 | 0.419 | 0.003 | 1.538 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **11.567** | **10.277** | **19.178** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 103 |
