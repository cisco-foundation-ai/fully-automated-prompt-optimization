# Evaluation Summary

Total cases: 300

## Composite Score
- average: 66.67

## Score Breakdown
- num_found: 2.64
- num_gold: 3.00
- num_missing: 0.36
- partial_recall: 88.00
- recall: 66.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.009 | 0.002 | 0.008 |
| summarize_hop1 | 3.401 | 2.641 | 7.044 |
| query_hop2 | 0.362 | 0.332 | 0.553 |
| retrieve_hop2 | 0.403 | 0.003 | 1.614 |
| summarize_hop2 | 8.726 | 7.531 | 13.190 |
| query_hop3 | 0.390 | 0.346 | 0.704 |
| retrieve_hop3 | 0.594 | 0.003 | 1.603 |
| summarize_hop3 | 13.158 | 10.156 | 18.426 |
| query_hop4 | 0.401 | 0.351 | 0.598 |
| retrieve_hop4 | 0.740 | 1.053 | 1.647 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **28.183** | **23.493** | **38.661** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop4 | 100 |
