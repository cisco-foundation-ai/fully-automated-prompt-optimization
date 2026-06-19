# Evaluation Summary

Total cases: 300

## Composite Score
- average: 62.67

## Score Breakdown
- num_found: 2.55
- num_gold: 3.00
- partial_recall: 85.11
- recall: 62.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.003 | 0.002 | 0.004 |
| summarize_hop1 | 4.891 | 4.049 | 8.538 |
| query_hop2 | 0.959 | 0.573 | 1.915 |
| retrieve_hop2 | 0.200 | 0.002 | 1.460 |
| summarize_hop2 | 4.360 | 3.819 | 7.525 |
| query_hop3 | 0.820 | 0.607 | 1.402 |
| retrieve_hop3 | 1.506 | 1.476 | 1.563 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **12.738** | **11.149** | **22.611** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 112 |
