# Evaluation Summary

Total cases: 300

## Composite Score
- average: 60.00

## Score Breakdown
- exact_match: 60.00
- f1: 68.28

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.027 | 0.002 | 0.012 |
| summarize_hop1 | 2.444 | 2.276 | 3.962 |
| query_hop2 | 1.372 | 1.308 | 1.876 |
| retrieve_hop2 | 0.614 | 0.003 | 1.602 |
| summarize_hop2 | 2.269 | 2.137 | 3.455 |
| answer | 1.024 | 0.955 | 1.510 |
| **Total** | **7.750** | **7.468** | **10.708** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 120 |
