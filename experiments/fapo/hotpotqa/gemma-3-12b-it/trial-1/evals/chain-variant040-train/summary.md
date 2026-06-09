# Evaluation Summary

Total cases: 150

## Composite Score
- average: 68.00

## Score Breakdown
- exact_match: 68.00
- f1: 73.82

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.078 | 0.002 | 0.059 |
| summarize_hop1 | 2.374 | 2.189 | 3.782 |
| query_hop2 | 1.111 | 1.040 | 1.538 |
| retrieve_hop2 | 0.453 | 0.003 | 1.539 |
| summarize_hop2 | 2.035 | 1.948 | 3.128 |
| answer | 1.037 | 0.982 | 1.494 |
| **Total** | **7.088** | **6.608** | **10.096** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 48 |
