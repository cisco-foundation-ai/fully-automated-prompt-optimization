# Evaluation Summary

Total cases: 300

## Composite Score
- average: 66.67

## Score Breakdown
- num_found: 2.62
- num_gold: 3.00
- partial_recall: 87.44
- recall: 66.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.003 | 0.002 | 0.005 |
| summarize_hop1 | 2.655 | 2.105 | 3.591 |
| query_hop2 | 0.772 | 0.676 | 1.033 |
| retrieve_hop2 | 0.800 | 0.268 | 1.639 |
| summarize_hop2 | 3.192 | 2.930 | 4.832 |
| query_hop3 | 0.790 | 0.564 | 1.114 |
| retrieve_hop3 | 0.643 | 0.002 | 1.603 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **8.856** | **7.887** | **14.739** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 100 |
