# Evaluation Summary

Total cases: 300

## Composite Score
- average: 74.00

## Score Breakdown
- num_found: 2.69
- num_gold: 3.00
- partial_recall: 89.67
- recall: 74.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.003 | 0.002 | 0.004 |
| summarize_hop1 | 2.728 | 2.439 | 4.626 |
| query_hop2 | 1.094 | 0.788 | 2.297 |
| retrieve_hop2 | 0.894 | 0.011 | 1.664 |
| summarize_hop2 | 3.731 | 3.295 | 7.292 |
| query_hop3 | 1.048 | 0.810 | 1.885 |
| retrieve_hop3 | 0.778 | 0.721 | 1.670 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **10.277** | **9.491** | **17.167** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 78 |
