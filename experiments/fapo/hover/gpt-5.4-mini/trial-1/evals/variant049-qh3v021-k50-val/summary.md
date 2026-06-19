# Evaluation Summary

Total cases: 300

## Composite Score
- average: 76.33

## Score Breakdown
- num_found: 2.73
- num_gold: 3.00
- partial_recall: 91.00
- recall: 76.33

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.010 | 0.002 | 0.006 |
| summarize_hop1 | 2.505 | 2.348 | 4.277 |
| query_hop2 | 0.964 | 0.775 | 1.545 |
| retrieve_hop2 | 0.562 | 0.002 | 1.663 |
| summarize_hop2 | 3.702 | 3.290 | 5.945 |
| query_hop3 | 1.102 | 0.839 | 1.824 |
| retrieve_hop3 | 1.591 | 1.548 | 1.678 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **10.434** | **9.692** | **16.304** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 71 |
