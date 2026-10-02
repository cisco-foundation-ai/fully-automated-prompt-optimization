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
| retrieve_hop1 | 0.032 | 0.002 | 0.010 |
| summarize_hop1 | 2.424 | 2.181 | 3.765 |
| query_hop2 | 0.761 | 0.675 | 1.089 |
| retrieve_hop2 | 0.595 | 0.002 | 1.683 |
| summarize_hop2 | 3.335 | 3.109 | 5.110 |
| query_hop3 | 0.762 | 0.685 | 1.177 |
| retrieve_hop3 | 0.342 | 0.002 | 1.620 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **8.251** | **7.793** | **11.948** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 78 |
| query_hop3 | 1 |
