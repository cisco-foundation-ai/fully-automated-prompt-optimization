# Evaluation Summary

Total cases: 300

## Composite Score
- average: 75.33

## Score Breakdown
- num_found: 2.71
- num_gold: 3.00
- num_missing: 0.29
- partial_recall: 90.22
- recall: 75.33

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.005 | 0.005 | 0.008 |
| summarize_hop1 | 3.469 | 2.620 | 7.306 |
| query_hop2 | 0.385 | 0.323 | 0.737 |
| retrieve_hop2 | 0.672 | 0.006 | 1.545 |
| summarize_hop2 | 6.134 | 5.772 | 9.527 |
| query_hop3 | 0.418 | 0.330 | 1.117 |
| retrieve_hop3 | 1.063 | 1.254 | 1.551 |
| summarize_hop3 | 6.980 | 6.717 | 12.012 |
| query_hop4 | 0.495 | 0.424 | 0.905 |
| retrieve_hop4 | 1.321 | 1.418 | 1.571 |
| query_hop5 | 0.438 | 0.363 | 1.002 |
| retrieve_hop5 | 1.308 | 1.364 | 1.571 |
| combine_retrievals | 0.000 | 0.000 | 0.001 |
| **Total** | **22.689** | **22.117** | **30.969** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop5 | 74 |
