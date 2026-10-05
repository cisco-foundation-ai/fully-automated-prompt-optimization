# Evaluation Summary

Total cases: 300

## Composite Score
- average: 16.33

## Score Breakdown
- num_found: 1.71
- num_gold: 3.00
- partial_recall: 57.11
- recall: 16.33

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.009 | 0.002 | 0.004 |
| summarize_hop1 | 2.570 | 2.021 | 5.567 |
| query_hop2 | 0.732 | 0.514 | 1.028 |
| retrieve_hop2 | 0.310 | 0.002 | 1.531 |
| summarize_hop2 | 2.972 | 2.339 | 5.930 |
| query_hop3 | 0.752 | 0.504 | 1.131 |
| retrieve_hop3 | 0.322 | 0.002 | 1.561 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **7.666** | **6.527** | **15.930** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 251 |
