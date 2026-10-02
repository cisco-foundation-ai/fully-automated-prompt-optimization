# Evaluation Summary

Total cases: 300

## Composite Score
- average: 61.67

## Score Breakdown
- exact_match: 61.67
- f1: 71.34

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.015 | 0.002 | 0.009 |
| summarize_hop1 | 2.290 | 2.145 | 3.963 |
| query_hop2 | 1.286 | 1.233 | 1.812 |
| retrieve_hop2 | 0.950 | 1.264 | 1.641 |
| summarize_hop2 | 2.297 | 2.228 | 3.540 |
| answer | 1.021 | 0.996 | 1.436 |
| **Total** | **7.859** | **7.462** | **11.205** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 115 |
