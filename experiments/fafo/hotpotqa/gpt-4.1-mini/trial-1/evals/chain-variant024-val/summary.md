# Evaluation Summary

Total cases: 300

## Composite Score
- average: 68.33

## Score Breakdown
- exact_match: 68.33
- f1: 76.54

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.015 | 0.002 | 0.008 |
| summarize_hop1 | 3.590 | 3.087 | 6.498 |
| query_hop2 | 1.993 | 1.691 | 3.372 |
| retrieve_hop2 | 0.435 | 0.002 | 1.313 |
| summarize_hop2 | 3.434 | 3.167 | 5.381 |
| answer | 1.665 | 1.401 | 3.057 |
| **Total** | **11.132** | **10.305** | **17.222** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 95 |
