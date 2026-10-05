# Evaluation Summary

Total cases: 300

## Composite Score
- average: 70.00

## Score Breakdown
- exact_match: 70.00
- f1: 77.73

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.027 | 0.002 | 0.006 |
| summarize_hop1 | 1.466 | 1.401 | 2.020 |
| query_hop2 | 1.011 | 0.958 | 1.471 |
| retrieve_hop2 | 0.603 | 0.002 | 1.620 |
| summarize_hop2 | 1.362 | 1.292 | 1.903 |
| answer | 0.954 | 0.873 | 1.390 |
| **Total** | **5.422** | **5.036** | **7.131** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 90 |
