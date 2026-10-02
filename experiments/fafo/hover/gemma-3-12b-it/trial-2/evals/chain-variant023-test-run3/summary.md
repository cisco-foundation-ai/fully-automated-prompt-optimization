# Evaluation Summary

Total cases: 300

## Composite Score
- average: 73.00

## Score Breakdown
- num_found: 2.69
- num_gold: 3.00
- num_missing: 0.31
- partial_recall: 89.78
- recall: 73.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.003 | 0.002 | 0.007 |
| summarize_hop1 | 3.331 | 2.617 | 7.209 |
| query_hop2 | 0.377 | 0.320 | 0.643 |
| retrieve_hop2 | 0.515 | 0.002 | 1.459 |
| summarize_hop2 | 6.793 | 5.985 | 9.752 |
| query_hop3 | 0.377 | 0.334 | 0.623 |
| retrieve_hop3 | 1.045 | 1.063 | 1.516 |
| summarize_hop3 | 8.664 | 6.486 | 12.470 |
| query_hop4 | 0.479 | 0.429 | 0.868 |
| retrieve_hop4 | 1.186 | 1.115 | 1.525 |
| query_hop5 | 0.449 | 0.367 | 0.956 |
| retrieve_hop5 | 1.209 | 1.131 | 1.520 |
| combine_retrievals | 0.000 | 0.000 | 0.001 |
| **Total** | **24.428** | **21.002** | **32.418** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop5 | 81 |
