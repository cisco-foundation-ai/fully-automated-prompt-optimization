# Evaluation Summary

Total cases: 300

## Composite Score
- average: 72.33

## Score Breakdown
- exact_match: 72.33
- f1: 78.91

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.042 | 0.002 | 0.009 |
| summarize_hop1 | 1.338 | 1.195 | 1.935 |
| query_hop2 | 1.224 | 1.040 | 1.530 |
| retrieve_hop2 | 0.340 | 0.002 | 1.319 |
| summarize_hop2 | 1.336 | 1.238 | 1.733 |
| answer | 0.947 | 0.877 | 1.297 |
| **Total** | **5.226** | **4.640** | **7.779** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 83 |
