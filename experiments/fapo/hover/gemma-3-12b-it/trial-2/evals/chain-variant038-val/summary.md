# Evaluation Summary

Total cases: 300

## Composite Score
- average: 78.33

## Score Breakdown
- num_found: 2.76
- num_gold: 3.00
- num_missing: 0.24
- partial_recall: 92.00
- recall: 78.33

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.003 | 0.002 | 0.005 |
| summarize_hop1 | 3.641 | 3.189 | 6.983 |
| query_hop2 | 0.427 | 0.344 | 0.877 |
| retrieve_hop2 | 0.900 | 1.269 | 1.612 |
| summarize_hop2 | 6.500 | 6.063 | 11.587 |
| query_hop3 | 0.521 | 0.391 | 1.390 |
| retrieve_hop3 | 2.213 | 2.532 | 3.250 |
| summarize_hop3 | 8.210 | 6.983 | 14.250 |
| query_hop4 | 0.553 | 0.446 | 1.258 |
| retrieve_hop4 | 2.519 | 2.623 | 3.270 |
| query_hop5 | 0.659 | 0.476 | 1.877 |
| retrieve_hop5 | 2.154 | 2.539 | 3.224 |
| combine_retrievals | 0.000 | 0.000 | 0.001 |
| **Total** | **28.301** | **26.941** | **38.483** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop5 | 65 |
