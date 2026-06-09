# Evaluation Summary

Total cases: 300

## Composite Score
- average: 61.67

## Score Breakdown
- num_found: 2.54
- num_gold: 3.00
- partial_recall: 84.67
- recall: 61.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.009 | 0.002 | 0.004 |
| summarize_hop1 | 4.915 | 4.229 | 8.744 |
| query_hop2 | 0.880 | 0.579 | 1.827 |
| retrieve_hop2 | 0.383 | 0.002 | 1.511 |
| summarize_hop2 | 4.385 | 3.891 | 7.211 |
| query_hop3 | 0.813 | 0.607 | 1.724 |
| retrieve_hop3 | 1.011 | 1.308 | 1.556 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **12.396** | **11.220** | **20.484** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 115 |
