# Evaluation Summary

Total cases: 300

## Composite Score
- average: 68.33

## Score Breakdown
- num_found: 2.63
- num_gold: 3.00
- num_missing: 0.37
- partial_recall: 87.78
- recall: 68.33

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| query_hop1 | 0.402 | 0.279 | 1.058 |
| retrieve_hop1 | 1.456 | 1.310 | 1.641 |
| summarize_hop1 | 2.682 | 2.310 | 5.366 |
| query_hop2 | 0.416 | 0.320 | 0.839 |
| retrieve_hop2 | 1.138 | 1.312 | 1.649 |
| summarize_hop2 | 6.648 | 5.727 | 9.774 |
| query_hop3 | 0.499 | 0.376 | 1.024 |
| retrieve_hop3 | 2.067 | 2.114 | 3.221 |
| summarize_hop3 | 7.536 | 6.375 | 12.373 |
| query_hop4 | 0.491 | 0.403 | 0.785 |
| retrieve_hop4 | 1.330 | 1.390 | 1.682 |
| query_hop5 | 0.548 | 0.461 | 1.064 |
| retrieve_hop5 | 2.100 | 2.108 | 3.239 |
| combine_retrievals | 0.000 | 0.000 | 0.001 |
| **Total** | **27.313** | **25.163** | **36.101** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop5 | 95 |
