# Evaluation Summary

Total cases: 300

## Composite Score
- average: 34.67

## Score Breakdown
- num_found: 2.09
- num_gold: 3.00
- num_missing: 0.91
- partial_recall: 69.67
- recall: 34.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.003 | 0.002 | 0.005 |
| summarize_hop1 | 1.750 | 1.620 | 2.694 |
| query_hop2 | 0.851 | 0.684 | 1.375 |
| retrieve_hop2 | 1.563 | 1.519 | 1.655 |
| summarize_hop2 | 2.320 | 2.054 | 3.413 |
| query_hop3 | 0.852 | 0.684 | 1.124 |
| retrieve_hop3 | 1.403 | 1.528 | 1.664 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **8.743** | **8.122** | **12.690** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 196 |
