# Evaluation Summary

Total cases: 300

## Composite Score
- average: 73.33

## Score Breakdown
- num_found: 2.68
- num_gold: 3.00
- partial_recall: 89.33
- recall: 73.33

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.025 | 0.002 | 0.010 |
| summarize_hop1 | 2.500 | 2.232 | 3.857 |
| query_hop2 | 0.757 | 0.705 | 1.048 |
| retrieve_hop2 | 0.916 | 1.068 | 1.684 |
| summarize_hop2 | 3.971 | 3.284 | 8.354 |
| query_hop3 | 0.876 | 0.720 | 1.650 |
| retrieve_hop3 | 0.415 | 0.002 | 1.625 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **9.460** | **8.562** | **16.000** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 80 |
