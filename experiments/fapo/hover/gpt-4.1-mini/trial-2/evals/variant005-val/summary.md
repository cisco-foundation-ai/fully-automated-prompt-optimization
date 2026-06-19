# Evaluation Summary

Total cases: 300

## Composite Score
- average: 19.33

## Score Breakdown
- num_found: 1.79
- num_gold: 3.00
- partial_recall: 59.56
- recall: 19.33

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.021 | 0.002 | 0.005 |
| summarize_hop1 | 3.526 | 2.939 | 7.570 |
| query_hop2 | 0.776 | 0.558 | 1.060 |
| retrieve_hop2 | 0.502 | 0.003 | 1.571 |
| summarize_hop2 | 4.470 | 3.503 | 10.259 |
| query_hop3 | 0.803 | 0.556 | 1.620 |
| retrieve_hop3 | 0.531 | 0.002 | 1.579 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **10.630** | **9.615** | **20.040** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 242 |
