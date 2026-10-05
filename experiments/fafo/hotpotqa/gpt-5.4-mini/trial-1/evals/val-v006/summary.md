# Evaluation Summary

Total cases: 300

## Composite Score
- average: 66.33

## Score Breakdown
- exact_match: 66.33
- f1: 73.78

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.058 | 0.002 | 0.110 |
| summarize_hop1 | 1.124 | 1.070 | 1.676 |
| query_hop2 | 1.076 | 1.026 | 1.476 |
| retrieve_hop2 | 1.090 | 0.502 | 1.716 |
| summarize_hop2 | 1.063 | 1.027 | 1.467 |
| answer | 0.790 | 0.736 | 1.263 |
| **Total** | **5.201** | **4.957** | **7.020** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 101 |
