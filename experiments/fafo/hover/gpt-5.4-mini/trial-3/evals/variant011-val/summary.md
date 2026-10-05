# Evaluation Summary

Total cases: 300

## Composite Score
- average: 23.67

## Score Breakdown
- num_found: 1.83
- num_gold: 3.00
- num_missing: 1.17
- partial_recall: 61.11
- recall: 23.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.003 | 0.002 | 0.006 |
| summarize_hop1 | 1.856 | 1.661 | 2.638 |
| query_hop2 | 0.877 | 0.752 | 1.078 |
| retrieve_hop2 | 1.171 | 1.312 | 1.612 |
| summarize_hop2 | 2.178 | 1.953 | 2.743 |
| query_hop3 | 0.867 | 0.737 | 1.204 |
| retrieve_hop3 | 1.102 | 1.313 | 1.611 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **8.054** | **7.582** | **11.462** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 229 |
