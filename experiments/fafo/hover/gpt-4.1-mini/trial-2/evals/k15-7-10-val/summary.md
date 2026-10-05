# Evaluation Summary

Total cases: 300

## Composite Score
- average: 25.67

## Score Breakdown
- num_found: 1.94
- num_gold: 3.00
- partial_recall: 64.67
- recall: 25.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.010 | 0.002 | 0.009 |
| summarize_hop1 | 3.084 | 2.755 | 5.068 |
| query_hop2 | 0.639 | 0.538 | 1.053 |
| retrieve_hop2 | 0.270 | 0.002 | 1.579 |
| summarize_hop2 | 3.488 | 2.872 | 6.641 |
| query_hop3 | 0.700 | 0.550 | 1.064 |
| retrieve_hop3 | 0.803 | 0.003 | 1.647 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **8.993** | **8.073** | **16.241** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 223 |
