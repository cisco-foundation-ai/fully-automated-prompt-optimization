# Evaluation Summary

Total cases: 300

## Composite Score
- average: 59.00

## Score Breakdown
- num_found: 2.51
- num_gold: 3.00
- num_missing: 0.49
- partial_recall: 83.56
- recall: 59.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.005 | 0.002 | 0.006 |
| summarize_hop1 | 3.188 | 2.748 | 5.446 |
| query_hop2 | 0.804 | 0.714 | 1.100 |
| retrieve_hop2 | 1.268 | 1.583 | 1.713 |
| summarize_hop2 | 3.706 | 3.070 | 6.796 |
| query_hop3 | 0.787 | 0.714 | 1.098 |
| retrieve_hop3 | 1.463 | 1.611 | 1.706 |
| summarize_hop3 | 3.319 | 2.903 | 5.982 |
| query_hop4 | 0.756 | 0.718 | 1.078 |
| retrieve_hop4 | 1.356 | 1.599 | 1.707 |
| combine_retrievals | 0.001 | 0.001 | 0.001 |
| **Total** | **16.652** | **16.088** | **24.879** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop4 | 123 |
