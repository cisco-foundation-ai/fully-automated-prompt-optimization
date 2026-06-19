# Evaluation Summary

Total cases: 300

## Composite Score
- average: 78.00

## Score Breakdown
- num_found: 2.76
- num_gold: 3.00
- num_missing: 0.24
- partial_recall: 92.11
- recall: 78.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.004 | 0.002 | 0.013 |
| summarize_hop1 | 3.371 | 2.930 | 6.708 |
| query_hop2 | 0.432 | 0.326 | 1.269 |
| retrieve_hop2 | 0.749 | 0.019 | 1.538 |
| summarize_hop2 | 6.444 | 6.048 | 10.654 |
| query_hop3 | 0.584 | 0.381 | 1.958 |
| retrieve_hop3 | 1.662 | 1.502 | 3.015 |
| summarize_hop3 | 7.205 | 6.892 | 12.570 |
| query_hop4 | 0.632 | 0.421 | 2.015 |
| retrieve_hop4 | 1.269 | 1.325 | 1.563 |
| query_hop5 | 0.702 | 0.538 | 1.720 |
| retrieve_hop5 | 3.694 | 3.830 | 4.551 |
| combine_retrievals | 0.000 | 0.000 | 0.001 |
| **Total** | **26.748** | **26.072** | **36.122** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop5 | 66 |
