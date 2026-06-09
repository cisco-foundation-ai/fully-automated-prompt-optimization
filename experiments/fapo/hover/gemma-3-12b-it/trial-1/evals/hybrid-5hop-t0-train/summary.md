# Evaluation Summary

Total cases: 150

## Composite Score
- average: 74.00

## Score Breakdown
- num_found: 2.73
- num_gold: 3.00
- num_missing: 0.27
- partial_recall: 91.11
- recall: 74.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.009 | 0.004 | 0.032 |
| extract_entities | 0.503 | 0.396 | 1.165 |
| retrieve_entities | 0.018 | 0.007 | 0.023 |
| summarize_hop1 | 4.049 | 3.455 | 10.668 |
| query_hop2 | 0.342 | 0.294 | 0.552 |
| retrieve_hop2 | 0.872 | 0.009 | 1.605 |
| summarize_hop2 | 3.048 | 2.275 | 6.912 |
| query_hop3 | 0.323 | 0.288 | 0.572 |
| retrieve_hop3 | 0.657 | 0.011 | 1.612 |
| summarize_hop3 | 2.572 | 1.864 | 5.542 |
| query_hop4 | 0.332 | 0.288 | 0.613 |
| retrieve_hop4 | 0.495 | 0.006 | 1.618 |
| summarize_hop4 | 3.445 | 1.809 | 5.932 |
| query_hop5 | 0.324 | 0.281 | 0.664 |
| retrieve_hop5 | 0.532 | 0.009 | 1.562 |
| combine_all | 0.011 | 0.010 | 0.016 |
| **Total** | **17.532** | **15.492** | **28.514** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop5_trunc | 39 |
