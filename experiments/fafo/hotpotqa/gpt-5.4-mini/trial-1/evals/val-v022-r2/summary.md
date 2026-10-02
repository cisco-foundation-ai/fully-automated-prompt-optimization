# Evaluation Summary

Total cases: 300

## Composite Score
- average: 69.33

## Score Breakdown
- exact_match: 69.33
- f1: 76.79

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.126 | 0.002 | 0.118 |
| summarize_hop1 | 1.321 | 1.206 | 1.928 |
| query_hop2 | 1.107 | 1.015 | 1.590 |
| retrieve_hop2 | 0.395 | 0.002 | 1.589 |
| summarize_hop2 | 1.477 | 1.381 | 2.220 |
| answer | 0.875 | 0.750 | 1.171 |
| **Total** | **5.302** | **4.649** | **7.067** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 90 |
| query_hop2 | 2 |
