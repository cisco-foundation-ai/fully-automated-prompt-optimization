# Evaluation Summary

Total cases: 300

## Composite Score
- average: 34.67

## Score Breakdown
- num_found: 2.13
- num_gold: 3.00
- num_missing: 0.87
- partial_recall: 71.11
- recall: 34.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.004 | 0.002 | 0.005 |
| summarize_hop1 | 1.804 | 1.605 | 2.611 |
| query_hop2 | 0.781 | 0.700 | 1.127 |
| retrieve_hop2 | 1.564 | 1.507 | 1.654 |
| summarize_hop2 | 2.160 | 1.978 | 3.365 |
| query_hop3 | 0.823 | 0.696 | 1.119 |
| retrieve_hop3 | 1.335 | 1.510 | 1.649 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **8.470** | **7.967** | **11.842** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 196 |
