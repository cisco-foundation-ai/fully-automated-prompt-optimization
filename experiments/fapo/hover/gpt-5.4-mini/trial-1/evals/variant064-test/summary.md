# Evaluation Summary

Total cases: 300

## Composite Score
- average: 84.67

## Score Breakdown
- num_found: 2.81
- num_gold: 3.00
- partial_recall: 93.67
- recall: 84.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.005 | 0.004 | 0.014 |
| summarize_hop1 | 3.183 | 2.843 | 5.340 |
| query_hop2 | 1.088 | 0.839 | 1.960 |
| retrieve_hop2 | 1.069 | 1.059 | 1.555 |
| summarize_hop2 | 4.759 | 4.143 | 8.882 |
| query_hop3 | 1.521 | 1.042 | 3.435 |
| retrieve_hop3 | 0.765 | 1.043 | 1.512 |
| query_hop4 | 1.621 | 1.140 | 3.717 |
| retrieve_hop4 | 1.136 | 1.099 | 1.551 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **15.147** | **14.028** | **23.370** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop4 | 46 |
