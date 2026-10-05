# Evaluation Summary

Total cases: 300

## Composite Score
- average: 21.33

## Score Breakdown
- num_found: 1.83
- num_gold: 3.00
- partial_recall: 60.89
- recall: 21.33

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.033 | 0.002 | 0.009 |
| summarize_hop1 | 2.449 | 1.993 | 4.083 |
| query_hop2 | 0.753 | 0.520 | 1.185 |
| retrieve_hop2 | 0.423 | 0.002 | 1.584 |
| summarize_hop2 | 2.878 | 2.405 | 4.802 |
| query_hop3 | 0.809 | 0.518 | 1.101 |
| retrieve_hop3 | 0.594 | 0.002 | 1.607 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **7.939** | **6.701** | **16.625** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 236 |
