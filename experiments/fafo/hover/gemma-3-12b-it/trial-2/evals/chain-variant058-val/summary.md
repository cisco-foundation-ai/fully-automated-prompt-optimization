# Evaluation Summary

Total cases: 300

## Composite Score
- average: 85.33

## Score Breakdown
- num_found: 2.83
- num_gold: 3.00
- num_missing: 0.17
- partial_recall: 94.44
- recall: 85.33

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.003 | 0.002 | 0.004 |
| summarize_hop1 | 3.136 | 2.813 | 5.887 |
| query_hop2 | 0.459 | 0.349 | 0.827 |
| retrieve_hop2 | 1.151 | 1.262 | 2.973 |
| summarize_hop2 | 6.053 | 5.885 | 9.767 |
| query_hop3 | 0.449 | 0.379 | 0.796 |
| retrieve_hop3 | 1.238 | 1.272 | 2.758 |
| summarize_hop3 | 6.733 | 6.506 | 10.766 |
| query_hop4 | 0.522 | 0.426 | 1.085 |
| retrieve_hop4 | 1.394 | 1.322 | 1.636 |
| query_hop5 | 0.622 | 0.477 | 1.755 |
| retrieve_hop5 | 1.989 | 1.990 | 3.073 |
| combine_retrievals | 0.000 | 0.000 | 0.001 |
| **Total** | **23.751** | **23.486** | **31.884** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop5 | 44 |
