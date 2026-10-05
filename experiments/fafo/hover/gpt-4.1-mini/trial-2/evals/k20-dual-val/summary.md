# Evaluation Summary

Total cases: 300

## Composite Score
- average: 28.00

## Score Breakdown
- num_found: 1.97
- num_gold: 3.00
- partial_recall: 65.78
- recall: 28.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.009 | 0.002 | 0.004 |
| summarize_hop1 | 4.291 | 3.609 | 8.367 |
| query_hop2 | 0.836 | 0.571 | 1.260 |
| retrieve_hop2 | 0.293 | 0.002 | 1.582 |
| summarize_hop2 | 4.857 | 3.605 | 10.654 |
| query_hop3 | 0.888 | 0.571 | 1.369 |
| retrieve_hop3 | 0.606 | 0.002 | 1.643 |
| retrieve_hop3b | 0.260 | 0.002 | 1.699 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **12.040** | **10.114** | **24.105** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3b | 216 |
