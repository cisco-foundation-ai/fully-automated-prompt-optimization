# Evaluation Summary

Total cases: 300

## Composite Score
- average: 73.67

## Score Breakdown
- num_found: 2.69
- num_gold: 3.00
- partial_recall: 89.78
- recall: 73.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.030 | 0.002 | 0.005 |
| summarize_hop1 | 2.505 | 2.259 | 4.089 |
| query_hop2 | 0.769 | 0.592 | 0.961 |
| retrieve_hop2 | 0.757 | 0.003 | 1.623 |
| summarize_hop2 | 3.464 | 3.148 | 5.668 |
| query_hop3 | 0.947 | 0.744 | 1.780 |
| retrieve_hop3 | 0.528 | 0.002 | 1.592 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **9.001** | **8.425** | **13.436** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 79 |
