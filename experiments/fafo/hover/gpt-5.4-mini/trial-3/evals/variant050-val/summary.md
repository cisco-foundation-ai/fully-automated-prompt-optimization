# Evaluation Summary

Total cases: 300

## Composite Score
- average: 58.00

## Score Breakdown
- num_found: 2.52
- num_gold: 3.00
- num_missing: 0.48
- partial_recall: 83.89
- recall: 58.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.004 | 0.002 | 0.009 |
| summarize_hop1 | 3.099 | 2.649 | 5.664 |
| query_hop2 | 0.832 | 0.720 | 1.142 |
| retrieve_hop2 | 1.560 | 1.562 | 1.698 |
| summarize_hop2 | 3.485 | 3.039 | 6.020 |
| query_hop3 | 0.770 | 0.704 | 1.075 |
| retrieve_hop3 | 1.267 | 1.371 | 1.681 |
| combine_retrievals | 0.000 | 0.000 | 0.001 |
| **Total** | **11.016** | **10.426** | **15.903** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 126 |
