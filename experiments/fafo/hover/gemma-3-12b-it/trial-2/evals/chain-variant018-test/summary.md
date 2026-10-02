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
| retrieve_hop1 | 0.003 | 0.002 | 0.008 |
| summarize_hop1 | 3.375 | 2.654 | 7.207 |
| query_hop2 | 0.362 | 0.330 | 0.611 |
| retrieve_hop2 | 1.568 | 1.579 | 1.716 |
| summarize_hop2 | 8.344 | 7.220 | 12.930 |
| query_hop3 | 0.378 | 0.338 | 0.552 |
| retrieve_hop3 | 1.264 | 1.559 | 1.700 |
| summarize_hop3 | 8.654 | 7.090 | 13.270 |
| query_hop4 | 0.462 | 0.436 | 0.607 |
| retrieve_hop4 | 1.526 | 1.625 | 1.730 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **25.936** | **22.828** | **36.029** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop4 | 81 |
