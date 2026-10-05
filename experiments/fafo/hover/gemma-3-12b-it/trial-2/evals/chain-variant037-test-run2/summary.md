# Evaluation Summary

Total cases: 300

## Composite Score
- average: 81.33

## Score Breakdown
- num_found: 2.79
- num_gold: 3.00
- num_missing: 0.21
- partial_recall: 92.89
- recall: 81.33

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.003 | 0.002 | 0.004 |
| summarize_hop1 | 3.527 | 2.943 | 7.180 |
| query_hop2 | 0.425 | 0.335 | 0.911 |
| retrieve_hop2 | 1.003 | 1.289 | 1.628 |
| summarize_hop2 | 6.667 | 6.266 | 11.443 |
| query_hop3 | 0.521 | 0.392 | 1.002 |
| retrieve_hop3 | 2.426 | 2.606 | 3.220 |
| summarize_hop3 | 8.941 | 6.942 | 13.568 |
| query_hop4 | 0.627 | 0.431 | 1.928 |
| retrieve_hop4 | 1.375 | 1.413 | 1.658 |
| query_hop5 | 0.615 | 0.486 | 1.409 |
| retrieve_hop5 | 2.335 | 2.609 | 3.217 |
| combine_retrievals | 0.000 | 0.000 | 0.001 |
| **Total** | **28.464** | **26.497** | **36.385** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop5 | 56 |
