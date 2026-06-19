# Evaluation Summary

Total cases: 300

## Composite Score
- average: 93.67

## Score Breakdown
- num_found: 2.93
- num_gold: 3.00
- partial_recall: 97.78
- recall: 93.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.993 | 0.562 | 1.726 |
| summarize_hop1 | 11.051 | 8.578 | 21.458 |
| query_hop2 | 0.846 | 0.758 | 1.191 |
| retrieve_hop2 | 6.629 | 6.700 | 8.217 |
| summarize_hop2 | 13.761 | 9.453 | 28.472 |
| query_hop3 | 0.896 | 0.698 | 1.287 |
| retrieve_hop3 | 5.009 | 5.316 | 8.138 |
| combine_retrievals | 0.001 | 0.001 | 0.003 |
| **Total** | **39.186** | **33.806** | **66.760** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 19 |
