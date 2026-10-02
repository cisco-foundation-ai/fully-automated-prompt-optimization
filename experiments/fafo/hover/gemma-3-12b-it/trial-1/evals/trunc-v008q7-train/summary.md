# Evaluation Summary

Total cases: 150

## Composite Score
- average: 68.00

## Score Breakdown
- num_found: 2.66
- num_gold: 3.00
- num_missing: 0.34
- partial_recall: 88.67
- recall: 68.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 1.298 | 1.137 | 1.736 |
| summarize_hop1 | 3.739 | 2.854 | 8.470 |
| query_hop2 | 0.365 | 0.304 | 0.705 |
| retrieve_hop2 | 1.139 | 1.282 | 1.614 |
| summarize_hop2 | 2.877 | 2.269 | 6.704 |
| query_hop3 | 0.330 | 0.292 | 0.514 |
| retrieve_hop3 | 1.176 | 1.279 | 1.615 |
| combine_retrievals | 0.005 | 0.005 | 0.008 |
| **Total** | **10.930** | **9.750** | **21.123** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3_trunc | 48 |
