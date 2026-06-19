# Evaluation Summary

Total cases: 300

## Composite Score
- average: 21.00

## Score Breakdown
- num_found: 1.80
- num_gold: 3.00
- num_missing: 1.20
- partial_recall: 59.89
- recall: 21.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.003 | 0.002 | 0.004 |
| summarize_hop1 | 1.635 | 1.506 | 2.386 |
| query_hop2 | 0.772 | 0.680 | 1.051 |
| retrieve_hop2 | 0.394 | 0.002 | 1.613 |
| summarize_hop2 | 1.826 | 1.684 | 2.564 |
| query_hop3 | 0.949 | 0.728 | 1.134 |
| retrieve_hop3 | 1.514 | 1.542 | 1.647 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **7.093** | **6.364** | **12.704** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 237 |
