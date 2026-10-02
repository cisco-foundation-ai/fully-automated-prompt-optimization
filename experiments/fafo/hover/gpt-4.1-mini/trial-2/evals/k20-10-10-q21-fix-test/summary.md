# Evaluation Summary

Total cases: 300

## Composite Score
- average: 62.00

## Score Breakdown
- num_found: 2.54
- num_gold: 3.00
- partial_recall: 84.78
- recall: 62.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.004 | 0.002 | 0.014 |
| summarize_hop1 | 3.775 | 3.373 | 5.691 |
| query_hop2 | 0.812 | 0.575 | 1.311 |
| retrieve_hop2 | 0.733 | 0.015 | 1.509 |
| summarize_hop2 | 3.895 | 3.352 | 6.189 |
| query_hop3 | 0.704 | 0.585 | 1.134 |
| retrieve_hop3 | 0.725 | 1.038 | 1.515 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **10.649** | **9.713** | **15.795** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 114 |
