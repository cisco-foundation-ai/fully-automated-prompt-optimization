# Evaluation Summary

Total cases: 300

## Composite Score
- average: 63.67

## Score Breakdown
- num_found: 2.57
- num_gold: 3.00
- partial_recall: 85.78
- recall: 63.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.003 | 0.002 | 0.004 |
| summarize_hop1 | 6.184 | 4.110 | 14.038 |
| query_hop2 | 1.863 | 0.594 | 4.711 |
| retrieve_hop2 | 1.175 | 1.051 | 1.537 |
| summarize_hop2 | 6.534 | 4.780 | 17.006 |
| query_hop3 | 1.385 | 0.615 | 3.006 |
| retrieve_hop3 | 0.621 | 0.007 | 1.506 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **17.765** | **12.569** | **44.953** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 109 |
