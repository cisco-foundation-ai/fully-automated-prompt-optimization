# Evaluation Summary

Total cases: 300

## Composite Score
- average: 74.67

## Score Breakdown
- num_found: 2.72
- num_gold: 3.00
- num_missing: 0.28
- partial_recall: 90.78
- recall: 74.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.003 | 0.002 | 0.009 |
| summarize_hop1 | 3.190 | 2.596 | 6.576 |
| query_hop2 | 0.352 | 0.315 | 0.472 |
| retrieve_hop2 | 0.414 | 0.002 | 1.511 |
| summarize_hop2 | 6.064 | 5.739 | 9.132 |
| query_hop3 | 0.368 | 0.328 | 0.689 |
| retrieve_hop3 | 1.052 | 1.277 | 1.565 |
| summarize_hop3 | 7.231 | 6.571 | 12.449 |
| query_hop4 | 0.479 | 0.418 | 0.730 |
| retrieve_hop4 | 1.345 | 1.453 | 1.585 |
| combine_retrievals | 0.000 | 0.000 | 0.001 |
| **Total** | **20.499** | **19.837** | **30.576** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop4 | 76 |
