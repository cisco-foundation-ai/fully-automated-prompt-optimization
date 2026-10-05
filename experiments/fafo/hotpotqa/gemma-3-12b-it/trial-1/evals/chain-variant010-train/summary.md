# Evaluation Summary

Total cases: 150

## Composite Score
- average: 68.00

## Score Breakdown
- exact_match: 68.00
- f1: 73.73

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.034 | 0.003 | 0.014 |
| summarize_hop1 | 2.351 | 2.114 | 4.518 |
| query_hop2 | 1.230 | 1.181 | 1.821 |
| retrieve_hop2 | 0.835 | 0.005 | 1.642 |
| summarize_hop2 | 2.241 | 2.216 | 3.219 |
| answer | 1.009 | 0.977 | 1.415 |
| **Total** | **7.700** | **7.231** | **11.722** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 48 |
