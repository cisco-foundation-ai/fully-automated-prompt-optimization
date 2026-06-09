# Evaluation Summary

Total cases: 300

## Composite Score
- average: 75.33

## Score Breakdown
- num_found: 2.72
- num_gold: 3.00
- num_missing: 0.28
- partial_recall: 90.56
- recall: 75.33

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.004 | 0.002 | 0.007 |
| summarize_hop1 | 3.485 | 2.853 | 7.769 |
| query_hop2 | 0.378 | 0.332 | 0.647 |
| retrieve_hop2 | 0.707 | 0.008 | 1.647 |
| summarize_hop2 | 7.630 | 6.168 | 9.689 |
| query_hop3 | 0.402 | 0.352 | 0.696 |
| retrieve_hop3 | 1.293 | 1.352 | 1.676 |
| summarize_hop3 | 7.211 | 6.634 | 12.515 |
| query_hop4 | 1.506 | 0.436 | 1.012 |
| retrieve_hop4 | 1.419 | 1.411 | 1.705 |
| combine_retrievals | 0.000 | 0.000 | 0.001 |
| **Total** | **24.036** | **21.248** | **30.665** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop4 | 74 |
