# Evaluation Summary

Total cases: 300

## Composite Score
- average: 69.33

## Score Breakdown
- num_found: 2.61
- num_gold: 3.00
- partial_recall: 87.00
- recall: 69.33

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.015 | 0.010 | 0.024 |
| summarize_hop1 | 5.193 | 3.681 | 12.619 |
| query_hop2 | 1.008 | 0.762 | 1.499 |
| retrieve_hop2 | 2.074 | 1.627 | 4.934 |
| summarize_hop2 | 4.970 | 3.819 | 11.887 |
| query_hop3 | 1.213 | 0.853 | 1.818 |
| retrieve_hop3 | 5.918 | 5.274 | 11.973 |
| retrieve_mining | 3.007 | 3.077 | 6.346 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **23.396** | **21.279** | **41.554** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_mining | 92 |
