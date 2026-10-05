# Evaluation Summary

Total cases: 300

## Composite Score
- average: 71.33

## Score Breakdown
- exact_match: 71.33
- f1: 78.98

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.027 | 0.002 | 0.005 |
| summarize_hop1 | 1.409 | 1.331 | 2.026 |
| query_hop2 | 1.024 | 0.944 | 1.498 |
| retrieve_hop2 | 0.862 | 1.061 | 1.630 |
| summarize_hop2 | 1.184 | 1.119 | 1.621 |
| answer | 0.899 | 0.859 | 1.264 |
| **Total** | **5.405** | **5.272** | **7.131** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 86 |
