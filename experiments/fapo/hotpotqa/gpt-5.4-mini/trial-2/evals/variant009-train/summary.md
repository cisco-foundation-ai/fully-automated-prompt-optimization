# Evaluation Summary

Total cases: 150

## Composite Score
- average: 56.00

## Score Breakdown
- exact_match: 56.00
- f1: 64.73

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.049 | 0.002 | 0.033 |
| summarize_hop1 | 2.294 | 2.123 | 3.161 |
| query_hop2 | 1.124 | 1.090 | 1.509 |
| retrieve_hop2 | 0.707 | 0.004 | 1.560 |
| summarize_hop2 | 1.717 | 1.702 | 2.327 |
| answer | 1.060 | 0.988 | 1.520 |
| **Total** | **6.951** | **6.271** | **9.932** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 66 |
