# Evaluation Summary

Total cases: 300

## Composite Score
- average: 29.00

## Score Breakdown
- num_found: 2.00
- num_gold: 3.00
- partial_recall: 66.67
- recall: 29.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.030 | 0.002 | 0.010 |
| summarize_hop1 | 4.309 | 3.765 | 8.492 |
| query_hop2 | 0.941 | 0.544 | 1.376 |
| retrieve_hop2 | 0.240 | 0.002 | 1.590 |
| summarize_hop2 | 4.496 | 3.686 | 8.245 |
| query_hop3 | 0.942 | 0.597 | 1.659 |
| retrieve_hop3 | 0.658 | 0.003 | 1.636 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **11.616** | **9.994** | **21.593** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 213 |
