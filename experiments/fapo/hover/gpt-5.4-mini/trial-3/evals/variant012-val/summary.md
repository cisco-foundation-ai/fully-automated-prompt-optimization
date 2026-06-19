# Evaluation Summary

Total cases: 300

## Composite Score
- average: 23.33

## Score Breakdown
- num_found: 1.83
- num_gold: 3.00
- num_missing: 1.17
- partial_recall: 61.11
- recall: 23.33

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.003 | 0.002 | 0.004 |
| summarize_hop1 | 1.728 | 1.579 | 2.555 |
| query_hop2 | 0.903 | 0.741 | 1.249 |
| retrieve_hop2 | 1.399 | 1.518 | 1.676 |
| summarize_hop2 | 2.126 | 1.925 | 2.847 |
| query_hop3 | 0.914 | 0.733 | 1.129 |
| retrieve_hop3 | 1.261 | 1.517 | 1.653 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **8.333** | **7.836** | **12.880** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 230 |
