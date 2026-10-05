# Evaluation Summary

Total cases: 300

## Composite Score
- average: 72.00

## Score Breakdown
- num_found: 2.68
- num_gold: 3.00
- partial_recall: 89.33
- recall: 72.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.003 | 0.002 | 0.006 |
| summarize_hop1 | 2.312 | 2.149 | 3.645 |
| query_hop2 | 0.818 | 0.737 | 1.258 |
| retrieve_hop2 | 1.356 | 1.300 | 1.656 |
| summarize_hop2 | 2.006 | 1.796 | 2.971 |
| query_hop3 | 0.816 | 0.599 | 0.900 |
| retrieve_hop3 | 1.270 | 1.278 | 1.608 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **8.580** | **7.970** | **12.552** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 84 |
