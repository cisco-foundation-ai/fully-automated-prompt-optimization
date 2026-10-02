# Evaluation Summary

Total cases: 300

## Composite Score
- average: 54.00

## Score Breakdown
- num_found: 2.48
- num_gold: 3.00
- num_missing: 0.52
- partial_recall: 82.56
- recall: 54.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.003 | 0.002 | 0.006 |
| summarize_hop1 | 3.098 | 2.681 | 5.472 |
| query_hop2 | 0.878 | 0.730 | 1.200 |
| retrieve_hop2 | 1.075 | 1.083 | 1.643 |
| summarize_hop2 | 3.606 | 2.963 | 6.358 |
| query_hop3 | 1.062 | 0.758 | 1.654 |
| retrieve_hop3 | 1.315 | 1.289 | 1.648 |
| combine_retrievals | 0.000 | 0.000 | 0.001 |
| **Total** | **11.037** | **10.277** | **19.777** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 138 |
