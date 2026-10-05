# Evaluation Summary

Total cases: 300

## Composite Score
- average: 66.67

## Score Breakdown
- num_found: 2.59
- num_gold: 3.00
- partial_recall: 86.44
- recall: 66.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.459 | 0.010 | 1.615 |
| summarize_hop1 | 5.080 | 3.787 | 12.345 |
| query_hop2 | 1.111 | 0.952 | 1.823 |
| retrieve_hop2 | 1.793 | 1.591 | 3.272 |
| summarize_hop2 | 4.808 | 3.653 | 9.996 |
| query_hop3 | 1.145 | 1.020 | 1.856 |
| retrieve_hop3 | 6.310 | 6.172 | 12.481 |
| retrieve_mining | 0.298 | 0.025 | 1.637 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **21.003** | **19.273** | **36.312** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_mining | 100 |
