# Evaluation Summary

Total cases: 300

## Composite Score
- average: 21.33

## Score Breakdown
- num_found: 1.80
- num_gold: 3.00
- num_missing: 1.20
- partial_recall: 59.89
- recall: 21.33

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.004 | 0.002 | 0.009 |
| summarize_hop1 | 1.650 | 1.553 | 2.512 |
| query_hop2 | 0.957 | 0.768 | 1.439 |
| retrieve_hop2 | 1.180 | 1.058 | 1.601 |
| summarize_hop2 | 1.802 | 1.748 | 2.520 |
| query_hop3 | 0.910 | 0.768 | 1.128 |
| retrieve_hop3 | 1.188 | 1.066 | 1.605 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **7.691** | **7.344** | **10.064** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 236 |
