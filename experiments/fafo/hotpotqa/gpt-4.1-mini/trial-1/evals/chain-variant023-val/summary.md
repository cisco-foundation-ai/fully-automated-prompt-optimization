# Evaluation Summary

Total cases: 300

## Composite Score
- average: 68.00

## Score Breakdown
- exact_match: 68.00
- f1: 75.17

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.023 | 0.002 | 0.009 |
| summarize_hop1 | 3.031 | 2.742 | 5.310 |
| query_hop2 | 1.685 | 1.530 | 2.642 |
| retrieve_hop2 | 0.458 | 0.002 | 1.591 |
| summarize_hop2 | 2.787 | 2.643 | 4.692 |
| answer | 1.641 | 1.485 | 2.769 |
| **Total** | **9.624** | **9.095** | **13.939** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 96 |
