# Evaluation Summary

Total cases: 300

## Composite Score
- average: 23.00

## Score Breakdown
- num_found: 1.84
- num_gold: 3.00
- partial_recall: 61.33
- recall: 23.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.024 | 0.002 | 0.005 |
| summarize_hop1 | 2.583 | 2.127 | 5.122 |
| query_hop2 | 0.834 | 0.516 | 1.743 |
| retrieve_hop2 | 0.462 | 0.002 | 1.558 |
| summarize_hop2 | 3.375 | 2.626 | 8.529 |
| query_hop3 | 0.949 | 0.539 | 1.593 |
| retrieve_hop3 | 0.668 | 0.003 | 1.590 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **8.895** | **7.354** | **19.138** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 231 |
