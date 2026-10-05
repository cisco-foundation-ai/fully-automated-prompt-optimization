# Evaluation Summary

Total cases: 300

## Composite Score
- average: 63.67

## Score Breakdown
- num_found: 2.61
- num_gold: 3.00
- num_missing: 0.39
- partial_recall: 86.89
- recall: 63.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 1.029 | 0.571 | 1.702 |
| summarize_hop1 | 4.565 | 4.303 | 6.726 |
| query_hop2 | 0.929 | 0.770 | 1.396 |
| retrieve_hop2 | 1.272 | 1.338 | 1.646 |
| summarize_hop2 | 3.212 | 2.800 | 6.170 |
| query_hop3 | 0.884 | 0.784 | 1.370 |
| retrieve_hop3 | 1.349 | 1.461 | 1.642 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **13.240** | **12.585** | **18.702** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 109 |
