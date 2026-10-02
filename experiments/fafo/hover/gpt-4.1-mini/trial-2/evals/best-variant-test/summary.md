# Evaluation Summary

Total cases: 300

## Composite Score
- average: 25.33

## Score Breakdown
- num_found: 1.87
- num_gold: 3.00
- partial_recall: 62.33
- recall: 25.33

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.008 | 0.002 | 0.005 |
| summarize_hop1 | 2.462 | 2.158 | 3.837 |
| query_hop2 | 0.635 | 0.540 | 0.889 |
| retrieve_hop2 | 0.510 | 0.002 | 1.653 |
| summarize_hop2 | 2.715 | 2.421 | 5.022 |
| query_hop3 | 0.620 | 0.540 | 0.909 |
| retrieve_hop3 | 0.979 | 1.317 | 1.676 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **7.930** | **7.389** | **11.540** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 224 |
