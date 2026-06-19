# Evaluation Summary

Total cases: 300

## Composite Score
- average: 60.67

## Score Breakdown
- num_found: 2.55
- num_gold: 3.00
- partial_recall: 85.11
- recall: 60.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.027 | 0.002 | 0.010 |
| summarize_hop1 | 4.906 | 4.163 | 8.553 |
| query_hop2 | 0.955 | 0.569 | 1.830 |
| retrieve_hop2 | 0.088 | 0.002 | 1.234 |
| summarize_hop2 | 5.035 | 4.312 | 8.751 |
| query_hop3 | 0.805 | 0.585 | 1.188 |
| retrieve_hop3 | 0.484 | 0.003 | 1.542 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **12.300** | **10.989** | **19.184** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 118 |
