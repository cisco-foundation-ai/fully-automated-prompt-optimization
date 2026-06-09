# Evaluation Summary

Total cases: 300

## Composite Score
- average: 70.33

## Score Breakdown
- num_found: 2.68
- num_gold: 3.00
- num_missing: 0.32
- partial_recall: 89.22
- recall: 70.33

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.006 | 0.003 | 0.009 |
| summarize_hop1 | 8.636 | 8.168 | 13.087 |
| query_hop2 | 1.001 | 0.800 | 1.703 |
| retrieve_hop2 | 1.606 | 1.578 | 1.685 |
| summarize_hop2 | 3.756 | 3.133 | 7.813 |
| query_hop3 | 0.977 | 0.788 | 1.397 |
| retrieve_hop3 | 1.479 | 1.582 | 1.691 |
| combine_retrievals | 0.000 | 0.000 | 0.001 |
| **Total** | **17.463** | **16.598** | **25.842** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 89 |
