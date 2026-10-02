# Evaluation Summary

Total cases: 300

## Composite Score
- average: 57.33

## Score Breakdown
- num_found: 2.50
- num_gold: 3.00
- num_missing: 0.50
- partial_recall: 83.44
- recall: 57.33

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 1.003 | 0.549 | 1.703 |
| summarize_hop1 | 2.754 | 2.300 | 4.870 |
| query_hop2 | 0.791 | 0.682 | 1.025 |
| retrieve_hop2 | 1.423 | 1.490 | 1.635 |
| summarize_hop2 | 3.319 | 2.763 | 5.822 |
| query_hop3 | 0.742 | 0.691 | 1.032 |
| retrieve_hop3 | 1.373 | 1.402 | 1.648 |
| combine_retrievals | 0.000 | 0.000 | 0.001 |
| **Total** | **11.405** | **10.517** | **16.693** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 128 |
