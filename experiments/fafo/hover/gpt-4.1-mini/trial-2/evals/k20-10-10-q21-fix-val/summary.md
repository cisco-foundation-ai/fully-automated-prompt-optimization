# Evaluation Summary

Total cases: 300

## Composite Score
- average: 68.00

## Score Breakdown
- num_found: 2.63
- num_gold: 3.00
- partial_recall: 87.56
- recall: 68.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.023 | 0.002 | 0.007 |
| summarize_hop1 | 3.822 | 3.266 | 6.262 |
| query_hop2 | 1.071 | 0.598 | 1.586 |
| retrieve_hop2 | 0.603 | 0.002 | 1.503 |
| summarize_hop2 | 3.920 | 3.314 | 7.213 |
| query_hop3 | 0.882 | 0.621 | 1.298 |
| retrieve_hop3 | 0.488 | 0.002 | 1.519 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **10.809** | **9.442** | **18.028** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 96 |
