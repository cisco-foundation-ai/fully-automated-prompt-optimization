# Evaluation Summary

Total cases: 300

## Composite Score
- average: 61.67

## Score Breakdown
- num_found: 2.54
- num_gold: 3.00
- partial_recall: 84.56
- recall: 61.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.003 | 0.002 | 0.005 |
| summarize_hop1 | 4.065 | 3.333 | 6.918 |
| query_hop2 | 1.008 | 0.577 | 1.319 |
| retrieve_hop2 | 0.870 | 1.041 | 1.491 |
| summarize_hop2 | 4.176 | 3.619 | 7.031 |
| query_hop3 | 1.105 | 0.587 | 1.332 |
| retrieve_hop3 | 1.225 | 1.212 | 1.522 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **12.453** | **10.846** | **26.099** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 115 |
