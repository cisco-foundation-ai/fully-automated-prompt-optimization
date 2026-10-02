# Evaluation Summary

Total cases: 75

## Composite Score
- average: 65.33

## Score Breakdown
- num_found: 2.57
- num_gold: 3.00
- partial_recall: 85.78
- recall: 65.33

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 1.297 | 0.027 | 3.850 |
| summarize_hop1 | 7.617 | 4.769 | 30.081 |
| query_hop2 | 1.019 | 0.852 | 2.100 |
| retrieve_hop2 | 5.626 | 4.231 | 11.113 |
| summarize_hop2 | 6.249 | 4.867 | 11.967 |
| query_hop3 | 1.662 | 0.966 | 4.188 |
| retrieve_hop3 | 11.444 | 9.270 | 33.887 |
| retrieve_mining | 22.046 | 21.905 | 37.982 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **56.960** | **51.798** | **105.593** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_mining | 26 |
