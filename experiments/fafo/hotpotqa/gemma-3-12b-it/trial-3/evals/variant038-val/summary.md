# Evaluation Summary

Total cases: 300

## Composite Score
- average: 57.33

## Score Breakdown
- exact_match: 57.33
- f1: 67.62

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.018 | 0.002 | 0.014 |
| summarize_hop1 | 2.307 | 2.125 | 3.945 |
| query_hop2 | 1.058 | 1.019 | 1.456 |
| retrieve_hop2 | 0.540 | 0.003 | 1.383 |
| summarize_hop2 | 3.432 | 3.248 | 5.744 |
| answer | 1.024 | 0.981 | 1.542 |
| **Total** | **8.379** | **7.957** | **12.423** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 128 |
