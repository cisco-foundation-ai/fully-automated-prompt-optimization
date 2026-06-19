# Evaluation Summary

Total cases: 300

## Composite Score
- average: 78.67

## Score Breakdown
- num_found: 2.76
- num_gold: 3.00
- num_missing: 0.24
- partial_recall: 92.00
- recall: 78.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.003 | 0.002 | 0.005 |
| summarize_hop1 | 3.300 | 2.954 | 6.287 |
| query_hop2 | 0.390 | 0.321 | 0.810 |
| retrieve_hop2 | 0.892 | 1.231 | 1.585 |
| summarize_hop2 | 7.632 | 5.978 | 11.010 |
| query_hop3 | 0.477 | 0.381 | 1.135 |
| retrieve_hop3 | 1.465 | 1.422 | 3.066 |
| summarize_hop3 | 6.931 | 6.728 | 11.698 |
| query_hop4 | 0.489 | 0.420 | 0.853 |
| retrieve_hop4 | 1.339 | 1.446 | 1.650 |
| query_hop5 | 0.523 | 0.463 | 0.945 |
| retrieve_hop5 | 2.043 | 2.009 | 3.125 |
| combine_retrievals | 0.000 | 0.000 | 0.001 |
| **Total** | **25.484** | **23.903** | **33.235** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop5 | 64 |
