# Evaluation Summary

Total cases: 300

## Composite Score
- average: 21.33

## Score Breakdown
- num_found: 1.82
- num_gold: 3.00
- partial_recall: 60.67
- recall: 21.33

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.025 | 0.002 | 0.005 |
| summarize_hop1 | 2.753 | 2.064 | 4.949 |
| query_hop2 | 0.876 | 0.524 | 1.171 |
| retrieve_hop2 | 0.300 | 0.002 | 1.540 |
| summarize_hop2 | 3.110 | 2.519 | 5.235 |
| query_hop3 | 0.928 | 0.511 | 1.562 |
| retrieve_hop3 | 0.591 | 0.002 | 1.576 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **8.582** | **6.984** | **19.699** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 236 |
