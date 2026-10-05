# Evaluation Summary

Total cases: 300

## Composite Score
- average: 63.00

## Score Breakdown
- num_found: 2.57
- num_gold: 3.00
- partial_recall: 85.67
- recall: 63.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.004 | 0.002 | 0.008 |
| summarize_hop1 | 4.330 | 3.634 | 7.205 |
| query_hop2 | 0.709 | 0.567 | 0.966 |
| retrieve_hop2 | 0.264 | 0.003 | 1.492 |
| summarize_hop2 | 4.050 | 3.625 | 6.231 |
| query_hop3 | 0.667 | 0.589 | 1.015 |
| retrieve_hop3 | 0.394 | 0.004 | 1.515 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **10.418** | **9.346** | **17.450** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 111 |
