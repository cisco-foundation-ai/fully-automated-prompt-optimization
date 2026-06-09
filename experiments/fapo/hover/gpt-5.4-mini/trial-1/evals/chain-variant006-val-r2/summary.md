# Evaluation Summary

Total cases: 300

## Composite Score
- average: 71.33

## Score Breakdown
- num_found: 2.66
- num_gold: 3.00
- partial_recall: 88.78
- recall: 71.33

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.003 | 0.002 | 0.007 |
| summarize_hop1 | 2.400 | 2.131 | 3.515 |
| query_hop2 | 0.936 | 0.749 | 1.240 |
| retrieve_hop2 | 1.210 | 1.322 | 1.652 |
| summarize_hop2 | 1.996 | 1.741 | 2.915 |
| query_hop3 | 0.647 | 0.611 | 1.000 |
| retrieve_hop3 | 0.200 | 0.002 | 1.559 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **7.393** | **6.801** | **10.531** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 86 |
