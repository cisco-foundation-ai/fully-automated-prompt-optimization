# Evaluation Summary

Total cases: 300

## Composite Score
- average: 69.33

## Score Breakdown
- num_found: 2.62
- num_gold: 3.00
- partial_recall: 87.22
- recall: 69.33

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.015 | 0.010 | 0.023 |
| summarize_hop1 | 5.650 | 4.013 | 13.790 |
| query_hop2 | 0.925 | 0.781 | 1.489 |
| retrieve_hop2 | 22.573 | 20.011 | 49.448 |
| summarize_hop2 | 5.261 | 4.380 | 10.806 |
| query_hop3 | 1.028 | 0.893 | 1.627 |
| retrieve_hop3 | 23.270 | 21.950 | 44.401 |
| retrieve_mining | 21.036 | 21.013 | 32.422 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **79.760** | **77.727** | **116.403** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_mining | 92 |
