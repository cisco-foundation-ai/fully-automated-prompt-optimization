# Evaluation Summary

Total cases: 300

## Composite Score
- average: 22.67

## Score Breakdown
- num_found: 1.85
- num_gold: 3.00
- partial_recall: 61.56
- recall: 22.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.008 | 0.002 | 0.005 |
| summarize_hop1 | 2.275 | 1.897 | 4.431 |
| query_hop2 | 0.728 | 0.518 | 0.856 |
| retrieve_hop2 | 0.471 | 0.002 | 1.555 |
| summarize_hop2 | 2.674 | 2.300 | 5.093 |
| query_hop3 | 0.694 | 0.534 | 1.264 |
| retrieve_hop3 | 0.662 | 0.003 | 1.583 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **7.513** | **6.678** | **14.070** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 232 |
