# Evaluation Summary

Total cases: 300

## Composite Score
- average: 36.33

## Score Breakdown
- num_found: 2.15
- num_gold: 3.00
- num_missing: 0.85
- partial_recall: 71.56
- recall: 36.33

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.012 | 0.002 | 0.011 |
| summarize_hop1 | 2.487 | 2.417 | 3.481 |
| query_hop2 | 0.727 | 0.678 | 1.045 |
| retrieve_hop2 | 1.389 | 1.494 | 1.646 |
| summarize_hop2 | 2.359 | 2.132 | 3.547 |
| query_hop3 | 0.737 | 0.698 | 1.041 |
| retrieve_hop3 | 1.217 | 1.486 | 1.633 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **8.928** | **8.659** | **11.236** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 191 |
