# Evaluation Summary

Total cases: 300

## Composite Score
- average: 77.00

## Score Breakdown
- num_found: 2.73
- num_gold: 3.00
- partial_recall: 90.89
- recall: 77.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.009 | 0.002 | 0.005 |
| summarize_hop1 | 2.302 | 2.117 | 3.808 |
| query_hop2 | 0.841 | 0.689 | 1.215 |
| retrieve_hop2 | 0.760 | 0.003 | 1.634 |
| summarize_hop2 | 3.435 | 3.050 | 6.275 |
| query_hop3 | 0.802 | 0.738 | 1.328 |
| retrieve_hop3 | 0.895 | 1.298 | 1.631 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **9.045** | **8.457** | **13.385** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 69 |
