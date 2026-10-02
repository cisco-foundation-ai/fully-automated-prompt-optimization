# Evaluation Summary

Total cases: 300

## Composite Score
- average: 70.00

## Score Breakdown
- exact_match: 70.00
- f1: 77.59

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 1.272 | 0.887 | 1.712 |
| summarize_hop1 | 1.360 | 1.272 | 2.159 |
| query_hop2 | 1.121 | 1.050 | 1.590 |
| retrieve_hop2 | 1.324 | 1.345 | 1.635 |
| summarize_hop2 | 1.625 | 1.501 | 2.409 |
| answer | 0.881 | 0.727 | 1.185 |
| **Total** | **7.582** | **7.033** | **9.553** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 90 |
