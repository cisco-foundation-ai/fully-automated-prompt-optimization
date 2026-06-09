# Evaluation Summary

Total cases: 300

## Composite Score
- average: 54.67

## Score Breakdown
- num_found: 2.36
- num_gold: 3.00
- partial_recall: 78.56
- recall: 54.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.003 | 0.003 | 0.006 |
| summarize_hop1 | 4.219 | 3.425 | 8.517 |
| query_hop2 | 1.244 | 0.986 | 2.190 |
| retrieve_hop2 | 1.559 | 1.455 | 1.658 |
| summarize_hop2 | 4.684 | 3.877 | 9.136 |
| query_hop3 | 1.475 | 1.094 | 2.689 |
| retrieve_hop3 | 1.295 | 1.405 | 1.650 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **14.479** | **12.910** | **25.476** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 136 |
