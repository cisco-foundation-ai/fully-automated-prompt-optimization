# Evaluation Summary

Total cases: 300

## Composite Score
- average: 71.00

## Score Breakdown
- exact_match: 71.00
- f1: 78.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.050 | 0.002 | 0.009 |
| summarize_hop1 | 1.281 | 1.188 | 1.928 |
| query_hop2 | 1.129 | 1.006 | 1.895 |
| retrieve_hop2 | 0.264 | 0.002 | 1.377 |
| summarize_hop2 | 1.330 | 1.234 | 1.861 |
| answer | 0.996 | 0.904 | 1.545 |
| **Total** | **5.050** | **4.642** | **7.543** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 87 |
