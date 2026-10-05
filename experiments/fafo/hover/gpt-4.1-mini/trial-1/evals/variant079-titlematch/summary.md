# Evaluation Summary

Total cases: 300

## Composite Score
- average: 71.00

## Score Breakdown
- num_found: 2.63
- num_gold: 3.00
- partial_recall: 87.78
- recall: 71.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.014 | 0.010 | 0.023 |
| summarize_hop1 | 5.764 | 3.668 | 11.842 |
| query_hop2 | 0.917 | 0.772 | 1.326 |
| retrieve_hop2 | 24.993 | 22.398 | 51.392 |
| summarize_hop2 | 4.723 | 4.001 | 9.365 |
| query_hop3 | 1.001 | 0.853 | 1.571 |
| retrieve_hop3 | 22.923 | 22.128 | 39.761 |
| retrieve_mining | 21.742 | 21.630 | 34.891 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **82.078** | **81.727** | **118.519** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_mining | 87 |
