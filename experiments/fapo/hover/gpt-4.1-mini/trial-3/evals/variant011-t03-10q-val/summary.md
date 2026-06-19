# Evaluation Summary

Total cases: 300

## Composite Score
- average: 94.67

## Score Breakdown
- num_found: 2.94
- num_gold: 3.00
- partial_recall: 98.00
- recall: 94.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.008 | 0.006 | 0.010 |
| summarize_hop1 | 41.970 | 25.327 | 134.557 |
| query_hop2 | 1.275 | 1.199 | 2.407 |
| retrieve_hop2 | 7.938 | 8.564 | 15.857 |
| summarize_hop2 | 75.100 | 28.641 | 271.267 |
| query_hop3 | 2.553 | 1.879 | 5.949 |
| retrieve_hop3 | 11.022 | 10.973 | 16.184 |
| combine_retrievals | 0.004 | 0.004 | 0.009 |
| **Total** | **139.869** | **81.169** | **428.152** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 15 |
| query_hop2 | 1 |
