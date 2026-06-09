# Evaluation Summary

Total cases: 300

## Composite Score
- average: 28.67

## Score Breakdown
- num_found: 1.99
- num_gold: 3.00
- partial_recall: 66.44
- recall: 28.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.014 | 0.002 | 0.005 |
| summarize_hop1 | 3.791 | 3.375 | 6.585 |
| query_hop2 | 0.675 | 0.552 | 1.468 |
| retrieve_hop2 | 0.380 | 0.002 | 1.609 |
| summarize_hop2 | 4.875 | 3.803 | 7.764 |
| query_hop3 | 0.857 | 0.589 | 1.408 |
| retrieve_hop3 | 0.555 | 0.002 | 1.629 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **11.145** | **9.542** | **17.619** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 214 |
