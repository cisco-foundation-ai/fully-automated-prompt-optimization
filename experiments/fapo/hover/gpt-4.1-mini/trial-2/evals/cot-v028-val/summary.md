# Evaluation Summary

Total cases: 300

## Composite Score
- average: 20.67

## Score Breakdown
- num_found: 1.80
- num_gold: 3.00
- partial_recall: 60.11
- recall: 20.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.007 | 0.002 | 0.007 |
| summarize_hop1 | 2.266 | 2.048 | 3.476 |
| query_hop2 | 0.711 | 0.500 | 1.004 |
| retrieve_hop2 | 0.142 | 0.002 | 1.070 |
| summarize_hop2 | 2.566 | 2.313 | 4.114 |
| query_hop3 | 2.640 | 2.542 | 4.720 |
| retrieve_hop3 | 0.723 | 0.003 | 1.608 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **9.055** | **8.407** | **13.826** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 238 |
