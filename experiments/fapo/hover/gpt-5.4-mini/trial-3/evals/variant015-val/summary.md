# Evaluation Summary

Total cases: 300

## Composite Score
- average: 24.00

## Score Breakdown
- num_found: 1.85
- num_gold: 3.00
- num_missing: 1.15
- partial_recall: 61.78
- recall: 24.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.004 | 0.002 | 0.006 |
| summarize_hop1 | 1.662 | 1.482 | 2.361 |
| query_hop2 | 0.961 | 0.746 | 1.178 |
| retrieve_hop2 | 1.574 | 1.518 | 1.655 |
| summarize_hop2 | 1.863 | 1.778 | 2.705 |
| query_hop3 | 0.799 | 0.745 | 1.229 |
| retrieve_hop3 | 1.362 | 1.504 | 1.663 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **8.224** | **7.692** | **10.619** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 228 |
