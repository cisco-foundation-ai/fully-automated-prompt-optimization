# Evaluation Summary

Total cases: 300

## Composite Score
- average: 65.33

## Score Breakdown
- num_found: 2.63
- num_gold: 3.00
- num_missing: 0.37
- partial_recall: 87.56
- recall: 65.33

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.003 | 0.002 | 0.004 |
| summarize_hop1 | 3.418 | 2.814 | 7.224 |
| query_hop2 | 0.352 | 0.320 | 0.547 |
| retrieve_hop2 | 0.633 | 0.003 | 1.655 |
| summarize_hop2 | 7.973 | 7.373 | 13.323 |
| query_hop3 | 0.380 | 0.337 | 0.676 |
| retrieve_hop3 | 0.652 | 0.003 | 1.651 |
| summarize_hop3 | 11.702 | 10.910 | 17.982 |
| query_hop4 | 0.381 | 0.345 | 0.597 |
| retrieve_hop4 | 1.368 | 1.542 | 1.696 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **26.863** | **25.114** | **41.168** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop4 | 104 |
