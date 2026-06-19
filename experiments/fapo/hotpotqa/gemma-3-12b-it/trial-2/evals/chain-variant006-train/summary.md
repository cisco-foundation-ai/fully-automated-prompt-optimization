# Evaluation Summary

Total cases: 150

## Composite Score
- average: 72.67

## Score Breakdown
- exact_match: 72.67
- f1: 77.36

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.069 | 0.003 | 0.058 |
| summarize_hop1 | 3.680 | 3.391 | 6.484 |
| query_hop2 | 1.264 | 1.125 | 2.262 |
| retrieve_hop2 | 0.350 | 0.002 | 1.532 |
| summarize_hop2 | 3.171 | 2.967 | 5.015 |
| answer | 1.040 | 0.933 | 1.779 |
| **Total** | **9.575** | **9.308** | **13.918** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 41 |
