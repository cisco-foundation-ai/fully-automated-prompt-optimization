# Evaluation Summary

Total cases: 150

## Composite Score
- average: 69.33

## Score Breakdown
- exact_match: 69.33
- f1: 74.76

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.018 | 0.002 | 0.012 |
| summarize_hop1 | 2.270 | 2.058 | 4.030 |
| query_hop2 | 1.302 | 1.224 | 1.870 |
| retrieve_hop2 | 1.115 | 0.009 | 1.709 |
| summarize_hop2 | 2.257 | 2.169 | 3.398 |
| answer | 0.808 | 0.798 | 1.140 |
| **Total** | **7.770** | **7.127** | **10.877** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 46 |
