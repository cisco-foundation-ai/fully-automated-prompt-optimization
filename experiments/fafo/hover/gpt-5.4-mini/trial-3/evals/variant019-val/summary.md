# Evaluation Summary

Total cases: 300

## Composite Score
- average: 23.33

## Score Breakdown
- num_found: 1.85
- num_gold: 3.00
- num_missing: 1.15
- partial_recall: 61.78
- recall: 23.33

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.003 | 0.002 | 0.004 |
| summarize_hop1 | 1.687 | 1.512 | 2.362 |
| query_hop2 | 0.984 | 0.802 | 1.303 |
| retrieve_hop2 | 1.438 | 1.135 | 1.632 |
| summarize_hop2 | 2.112 | 1.922 | 2.808 |
| query_hop3 | 1.007 | 0.806 | 1.214 |
| retrieve_hop3 | 1.246 | 1.118 | 1.602 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **8.477** | **7.812** | **14.115** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 230 |
