# Evaluation Summary

Total cases: 300

## Composite Score
- average: 65.00

## Score Breakdown
- num_found: 2.56
- num_gold: 3.00
- partial_recall: 85.33
- recall: 65.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.015 | 0.010 | 0.026 |
| summarize_hop1 | 2.971 | 2.385 | 7.165 |
| query_hop2 | 1.153 | 0.864 | 2.444 |
| retrieve_hop2 | 3.602 | 1.590 | 15.637 |
| summarize_hop2 | 3.117 | 2.359 | 6.016 |
| query_hop3 | 1.371 | 0.979 | 3.384 |
| retrieve_hop3 | 6.179 | 3.272 | 21.827 |
| retrieve_mining | 1.283 | 1.079 | 4.599 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **19.691** | **14.349** | **49.391** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_mining | 105 |
