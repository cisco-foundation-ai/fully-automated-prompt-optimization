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
| retrieve_hop1 | 4.585 | 4.251 | 7.772 |
| summarize_hop1 | 3.914 | 3.276 | 9.902 |
| query_hop2 | 0.318 | 0.283 | 0.572 |
| retrieve_hop2 | 1.338 | 1.476 | 1.659 |
| summarize_hop2 | 3.029 | 2.294 | 7.485 |
| query_hop3 | 0.305 | 0.275 | 0.546 |
| retrieve_hop3 | 1.365 | 1.466 | 1.659 |
| combine_retrievals | 0.008 | 0.008 | 0.013 |
| **Total** | **14.861** | **14.069** | **26.148** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3_trunc | 39 |
