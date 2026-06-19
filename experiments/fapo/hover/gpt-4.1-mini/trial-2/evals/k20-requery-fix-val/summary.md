# Evaluation Summary

Total cases: 300

## Composite Score
- average: 63.00

## Score Breakdown
- num_found: 2.57
- num_gold: 3.00
- partial_recall: 85.56
- recall: 63.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.009 | 0.002 | 0.008 |
| summarize_hop1 | 4.167 | 3.554 | 7.028 |
| query_hop2 | 1.065 | 0.573 | 1.214 |
| retrieve_hop2 | 0.224 | 0.002 | 1.449 |
| summarize_hop2 | 4.046 | 3.597 | 7.415 |
| query_hop3 | 0.815 | 0.584 | 1.220 |
| retrieve_hop3 | 0.527 | 0.002 | 1.545 |
| retrieve_hop3b | 0.174 | 0.002 | 1.472 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **11.027** | **9.507** | **17.680** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3b | 111 |
