# Evaluation Summary

Total cases: 300

## Composite Score
- average: 66.33

## Score Breakdown
- num_found: 2.58
- num_gold: 3.00
- partial_recall: 86.00
- recall: 66.33

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.015 | 0.010 | 0.024 |
| summarize_hop1 | 5.129 | 3.502 | 14.600 |
| query_hop2 | 1.076 | 0.740 | 1.828 |
| retrieve_hop2 | 2.274 | 1.605 | 4.824 |
| summarize_hop2 | 5.011 | 3.689 | 12.627 |
| query_hop3 | 1.193 | 0.860 | 2.078 |
| retrieve_hop3 | 6.459 | 6.277 | 12.868 |
| retrieve_mining | 0.520 | 0.022 | 2.243 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **21.677** | **19.435** | **37.846** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_mining | 101 |
