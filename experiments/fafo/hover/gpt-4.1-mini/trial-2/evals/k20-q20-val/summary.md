# Evaluation Summary

Total cases: 300

## Composite Score
- average: 28.33

## Score Breakdown
- num_found: 1.98
- num_gold: 3.00
- partial_recall: 66.11
- recall: 28.33

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.011 | 0.002 | 0.004 |
| summarize_hop1 | 3.570 | 3.031 | 6.049 |
| query_hop2 | 0.967 | 0.583 | 1.914 |
| retrieve_hop2 | 0.423 | 0.002 | 1.652 |
| summarize_hop2 | 3.740 | 3.117 | 7.960 |
| query_hop3 | 1.014 | 0.569 | 1.998 |
| retrieve_hop3 | 0.800 | 0.003 | 1.675 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **10.524** | **9.258** | **18.101** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 215 |
