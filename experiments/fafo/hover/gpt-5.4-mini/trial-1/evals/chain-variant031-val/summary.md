# Evaluation Summary

Total cases: 300

## Composite Score
- average: 72.33

## Score Breakdown
- num_found: 2.68
- num_gold: 3.00
- partial_recall: 89.33
- recall: 72.33

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.015 | 0.002 | 0.008 |
| summarize_hop1 | 2.764 | 2.626 | 4.293 |
| query_hop2 | 0.673 | 0.562 | 1.086 |
| retrieve_hop2 | 0.660 | 0.002 | 1.626 |
| summarize_hop2 | 3.192 | 2.811 | 5.414 |
| query_hop3 | 0.887 | 0.746 | 1.451 |
| retrieve_hop3 | 1.108 | 1.519 | 1.673 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **9.298** | **8.935** | **13.363** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 83 |
