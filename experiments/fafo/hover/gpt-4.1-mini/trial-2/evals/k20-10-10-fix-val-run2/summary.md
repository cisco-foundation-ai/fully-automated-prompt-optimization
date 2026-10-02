# Evaluation Summary

Total cases: 300

## Composite Score
- average: 61.67

## Score Breakdown
- num_found: 2.55
- num_gold: 3.00
- partial_recall: 85.11
- recall: 61.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.028 | 0.002 | 0.009 |
| summarize_hop1 | 4.626 | 4.068 | 7.846 |
| query_hop2 | 0.768 | 0.567 | 1.201 |
| retrieve_hop2 | 0.154 | 0.002 | 1.267 |
| summarize_hop2 | 4.734 | 4.229 | 8.321 |
| query_hop3 | 0.743 | 0.602 | 1.522 |
| retrieve_hop3 | 0.528 | 0.003 | 1.532 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **11.582** | **10.500** | **19.948** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 115 |
