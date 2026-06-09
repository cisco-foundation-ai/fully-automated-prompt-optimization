# Evaluation Summary

Total cases: 300

## Composite Score
- average: 79.00

## Score Breakdown
- num_found: 2.77
- num_gold: 3.00
- partial_recall: 92.33
- recall: 79.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.003 | 0.002 | 0.005 |
| summarize_hop1 | 3.059 | 2.751 | 5.041 |
| query_hop2 | 1.209 | 0.813 | 2.571 |
| retrieve_hop2 | 1.531 | 1.418 | 1.560 |
| summarize_hop2 | 5.155 | 4.357 | 9.227 |
| query_hop3 | 1.464 | 1.009 | 3.248 |
| retrieve_hop3 | 0.611 | 0.003 | 1.468 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **13.032** | **11.920** | **21.418** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 63 |
