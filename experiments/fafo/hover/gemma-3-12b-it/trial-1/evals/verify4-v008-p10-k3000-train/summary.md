# Evaluation Summary

Total cases: 150

## Composite Score
- average: 89.33

## Score Breakdown
- num_found: 2.89
- num_gold: 3.00
- num_missing: 0.11
- partial_recall: 96.44
- recall: 89.33

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 5.706 | 5.146 | 11.367 |
| summarize_hop1 | 1.579 | 1.390 | 3.033 |
| retrieve_hop2 | 4.763 | 4.963 | 8.234 |
| summarize_hop2 | 1.374 | 1.185 | 2.847 |
| retrieve_hop3 | 2.436 | 1.679 | 5.431 |
| summarize_hop3 | 1.300 | 1.127 | 2.569 |
| retrieve_hop4 | 1.522 | 1.377 | 4.143 |
| combine_retrievals | 0.028 | 0.026 | 0.054 |
| **Total** | **18.707** | **18.098** | **27.334** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop4_trunc | 16 |
