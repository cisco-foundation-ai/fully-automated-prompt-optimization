# Evaluation Summary

Total cases: 150

## Composite Score
- average: 72.00

## Score Breakdown
- exact_match: 72.00
- f1: 77.90

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.004 | 0.002 | 0.007 |
| summarize_hop1 | 3.166 | 2.627 | 6.532 |
| query_hop2 | 1.975 | 1.882 | 3.206 |
| retrieve_hop2 | 1.721 | 1.573 | 1.696 |
| summarize_hop2 | 2.698 | 2.442 | 4.187 |
| answer | 1.579 | 1.462 | 2.665 |
| **Total** | **11.143** | **10.249** | **22.281** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 42 |
