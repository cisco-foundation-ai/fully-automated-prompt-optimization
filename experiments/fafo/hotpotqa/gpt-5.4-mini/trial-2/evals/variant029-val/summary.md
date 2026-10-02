# Evaluation Summary

Total cases: 300

## Composite Score
- average: 72.00

## Score Breakdown
- exact_match: 72.00
- f1: 78.48

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.045 | 0.002 | 0.009 |
| summarize_hop1 | 2.317 | 2.173 | 3.305 |
| query_hop2 | 1.340 | 1.128 | 1.832 |
| retrieve_hop2 | 0.337 | 0.002 | 1.561 |
| summarize_hop2 | 1.655 | 1.583 | 2.279 |
| answer | 1.029 | 0.835 | 1.590 |
| **Total** | **6.724** | **6.128** | **9.904** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 84 |
