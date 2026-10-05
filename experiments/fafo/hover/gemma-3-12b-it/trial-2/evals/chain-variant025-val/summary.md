# Evaluation Summary

Total cases: 300

## Composite Score
- average: 77.00

## Score Breakdown
- num_found: 2.74
- num_gold: 3.00
- num_missing: 0.26
- partial_recall: 91.33
- recall: 77.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.003 | 0.002 | 0.005 |
| summarize_hop1 | 3.362 | 2.760 | 7.266 |
| query_hop2 | 0.391 | 0.325 | 0.633 |
| retrieve_hop2 | 0.367 | 0.002 | 1.481 |
| summarize_hop2 | 6.618 | 6.025 | 11.654 |
| query_hop3 | 0.398 | 0.343 | 0.732 |
| retrieve_hop3 | 1.094 | 1.244 | 1.562 |
| summarize_hop3 | 7.983 | 6.702 | 13.499 |
| query_hop4 | 0.544 | 0.458 | 0.981 |
| retrieve_hop4 | 1.319 | 1.307 | 1.566 |
| summarize_hop4 | 9.163 | 7.078 | 14.934 |
| query_hop5 | 0.458 | 0.393 | 0.831 |
| retrieve_hop5 | 1.289 | 1.296 | 1.588 |
| combine_retrievals | 0.000 | 0.000 | 0.001 |
| **Total** | **32.989** | **29.933** | **45.571** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop5 | 69 |
