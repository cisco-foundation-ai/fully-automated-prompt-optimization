# Evaluation Summary

Total cases: 300

## Composite Score
- average: 25.33

## Score Breakdown
- num_found: 1.86
- num_gold: 3.00
- num_missing: 1.14
- partial_recall: 62.11
- recall: 25.33

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.004 | 0.002 | 0.004 |
| summarize_hop1 | 1.601 | 1.459 | 2.478 |
| query_hop2 | 1.233 | 1.035 | 2.074 |
| retrieve_hop2 | 1.103 | 1.132 | 1.696 |
| summarize_hop2 | 1.822 | 1.753 | 2.598 |
| query_hop3 | 1.230 | 0.963 | 1.698 |
| retrieve_hop3 | 1.116 | 1.326 | 1.675 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **8.109** | **7.624** | **11.337** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 224 |
