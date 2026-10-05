# Evaluation Summary

Total cases: 300

## Composite Score
- average: 79.33

## Score Breakdown
- num_found: 2.77
- num_gold: 3.00
- num_missing: 0.23
- partial_recall: 92.44
- recall: 79.33

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.003 | 0.002 | 0.005 |
| summarize_hop1 | 3.586 | 2.978 | 7.429 |
| query_hop2 | 0.481 | 0.340 | 1.125 |
| retrieve_hop2 | 1.002 | 1.236 | 1.612 |
| summarize_hop2 | 7.059 | 6.417 | 12.772 |
| query_hop3 | 0.665 | 0.469 | 1.837 |
| retrieve_hop3 | 3.933 | 4.051 | 4.803 |
| summarize_hop3 | 7.378 | 7.012 | 13.053 |
| query_hop4 | 0.696 | 0.438 | 2.261 |
| retrieve_hop4 | 1.364 | 1.478 | 1.652 |
| query_hop5 | 0.730 | 0.506 | 2.094 |
| retrieve_hop5 | 2.137 | 2.103 | 3.199 |
| combine_retrievals | 0.000 | 0.000 | 0.001 |
| **Total** | **29.036** | **28.278** | **40.204** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop5 | 62 |
