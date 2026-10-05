# Evaluation Summary

Total cases: 150

## Composite Score
- average: 71.33

## Score Breakdown
- exact_match: 71.33
- f1: 78.52

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.039 | 0.003 | 0.023 |
| summarize_hop1 | 2.078 | 1.841 | 3.892 |
| query_hop2 | 1.056 | 0.999 | 1.502 |
| retrieve_hop2 | 0.695 | 0.007 | 1.567 |
| summarize_hop2 | 3.282 | 3.176 | 5.796 |
| answer | 1.105 | 1.043 | 1.707 |
| **Total** | **8.255** | **7.780** | **12.191** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 43 |
