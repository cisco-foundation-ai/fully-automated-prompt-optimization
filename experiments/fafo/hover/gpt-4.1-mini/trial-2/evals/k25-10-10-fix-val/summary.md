# Evaluation Summary

Total cases: 300

## Composite Score
- average: 63.67

## Score Breakdown
- num_found: 2.57
- num_gold: 3.00
- partial_recall: 85.56
- recall: 63.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.009 | 0.002 | 0.004 |
| summarize_hop1 | 4.540 | 3.617 | 6.938 |
| query_hop2 | 0.750 | 0.551 | 1.338 |
| retrieve_hop2 | 0.162 | 0.002 | 1.400 |
| summarize_hop2 | 4.347 | 3.648 | 6.728 |
| query_hop3 | 0.995 | 0.581 | 1.463 |
| retrieve_hop3 | 0.600 | 0.002 | 1.541 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **11.403** | **9.557** | **17.146** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 109 |
