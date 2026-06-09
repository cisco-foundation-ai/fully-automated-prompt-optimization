# Evaluation Summary

Total cases: 300

## Composite Score
- average: 26.33

## Score Breakdown
- num_found: 1.87
- num_gold: 3.00
- num_missing: 1.13
- partial_recall: 62.44
- recall: 26.33

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.004 | 0.002 | 0.010 |
| summarize_hop1 | 1.747 | 1.550 | 2.493 |
| query_hop2 | 0.885 | 0.754 | 1.272 |
| retrieve_hop2 | 1.273 | 1.300 | 1.637 |
| summarize_hop2 | 2.052 | 1.837 | 2.729 |
| query_hop3 | 0.918 | 0.764 | 1.146 |
| retrieve_hop3 | 1.199 | 1.293 | 1.644 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **8.078** | **7.425** | **11.743** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 221 |
