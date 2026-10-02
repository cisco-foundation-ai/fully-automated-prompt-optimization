# Evaluation Summary

Total cases: 300

## Composite Score
- average: 59.67

## Score Breakdown
- num_found: 2.50
- num_gold: 3.00
- partial_recall: 83.33
- recall: 59.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.016 | 0.002 | 0.008 |
| summarize_hop1 | 3.642 | 3.242 | 5.932 |
| query_hop2 | 0.749 | 0.559 | 1.069 |
| retrieve_hop2 | 0.356 | 0.002 | 1.488 |
| summarize_hop2 | 3.934 | 3.237 | 6.206 |
| query_hop3 | 0.747 | 0.585 | 1.171 |
| retrieve_hop3 | 0.951 | 1.251 | 1.551 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **10.394** | **9.409** | **14.932** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 121 |
