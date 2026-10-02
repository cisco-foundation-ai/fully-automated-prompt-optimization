# Evaluation Summary

Total cases: 300

## Composite Score
- average: 69.67

## Score Breakdown
- num_found: 2.66
- num_gold: 3.00
- partial_recall: 88.67
- recall: 69.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.003 | 0.002 | 0.004 |
| summarize_hop1 | 2.455 | 2.018 | 3.608 |
| query_hop2 | 0.953 | 0.762 | 1.647 |
| retrieve_hop2 | 1.407 | 1.357 | 1.679 |
| summarize_hop2 | 1.972 | 1.820 | 2.895 |
| query_hop3 | 0.856 | 0.704 | 1.285 |
| retrieve_hop3 | 1.380 | 1.498 | 1.657 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **9.025** | **8.310** | **13.783** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 91 |
