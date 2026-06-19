# Evaluation Summary

Total cases: 150

## Composite Score
- average: 70.67

## Score Breakdown
- num_found: 2.69
- num_gold: 3.00
- num_missing: 0.31
- partial_recall: 89.78
- recall: 70.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.021 | 0.004 | 0.028 |
| summarize_hop1 | 4.082 | 3.540 | 9.625 |
| query_hop2 | 0.318 | 0.293 | 0.541 |
| retrieve_hop2 | 0.935 | 1.051 | 1.667 |
| summarize_hop2 | 3.114 | 2.387 | 6.956 |
| query_hop3 | 0.325 | 0.279 | 0.617 |
| retrieve_hop3 | 1.312 | 1.306 | 1.653 |
| combine_retrievals | 0.005 | 0.005 | 0.008 |
| **Total** | **10.112** | **9.102** | **22.160** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3_trunc | 44 |
