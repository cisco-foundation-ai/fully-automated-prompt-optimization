# Evaluation Summary

Total cases: 300

## Composite Score
- average: 77.00

## Score Breakdown
- num_found: 2.74
- num_gold: 3.00
- num_missing: 0.26
- partial_recall: 91.44
- recall: 77.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.003 | 0.002 | 0.005 |
| summarize_hop1 | 3.390 | 2.827 | 7.126 |
| query_hop2 | 0.357 | 0.321 | 0.586 |
| retrieve_hop2 | 0.821 | 0.004 | 1.559 |
| summarize_hop2 | 6.841 | 5.953 | 9.384 |
| query_hop3 | 0.378 | 0.329 | 0.619 |
| retrieve_hop3 | 1.134 | 1.435 | 1.587 |
| summarize_hop3 | 7.670 | 6.491 | 13.431 |
| query_hop4 | 0.506 | 0.424 | 0.929 |
| retrieve_hop4 | 1.404 | 1.490 | 1.609 |
| query_hop5 | 0.406 | 0.372 | 0.607 |
| retrieve_hop5 | 1.433 | 1.480 | 1.605 |
| combine_retrievals | 0.000 | 0.000 | 0.001 |
| **Total** | **24.344** | **21.873** | **33.503** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop5 | 69 |
