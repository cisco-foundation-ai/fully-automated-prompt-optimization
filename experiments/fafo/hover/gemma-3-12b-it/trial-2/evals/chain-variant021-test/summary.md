# Evaluation Summary

Total cases: 300

## Composite Score
- average: 74.00

## Score Breakdown
- num_found: 2.71
- num_gold: 3.00
- num_missing: 0.29
- partial_recall: 90.33
- recall: 74.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.003 | 0.002 | 0.003 |
| summarize_hop1 | 5.420 | 5.316 | 8.337 |
| query_hop2 | 1.364 | 0.315 | 0.592 |
| retrieve_hop2 | 1.310 | 1.466 | 1.663 |
| summarize_hop2 | 7.858 | 6.078 | 10.208 |
| query_hop3 | 0.380 | 0.331 | 0.735 |
| retrieve_hop3 | 1.340 | 1.512 | 1.661 |
| summarize_hop3 | 8.713 | 7.619 | 13.902 |
| query_hop4 | 0.472 | 0.413 | 0.695 |
| retrieve_hop4 | 1.455 | 1.569 | 1.698 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **28.315** | **24.383** | **35.707** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop4 | 78 |
