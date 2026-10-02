# Evaluation Summary

Total cases: 300

## Composite Score
- average: 69.33

## Score Breakdown
- num_found: 2.67
- num_gold: 3.00
- num_missing: 0.33
- partial_recall: 88.89
- recall: 69.33

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 1.043 | 1.101 | 1.665 |
| summarize_hop1 | 8.624 | 8.187 | 13.095 |
| query_hop2 | 0.962 | 0.772 | 1.745 |
| retrieve_hop2 | 1.240 | 1.220 | 1.587 |
| summarize_hop2 | 3.608 | 2.960 | 6.955 |
| query_hop3 | 0.944 | 0.740 | 1.461 |
| retrieve_hop3 | 1.221 | 1.207 | 1.585 |
| combine_retrievals | 0.000 | 0.000 | 0.001 |
| **Total** | **17.642** | **16.622** | **26.647** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 92 |
