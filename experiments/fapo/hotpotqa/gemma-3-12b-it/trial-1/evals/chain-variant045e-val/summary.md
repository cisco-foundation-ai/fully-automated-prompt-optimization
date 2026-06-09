# Evaluation Summary

Total cases: 300

## Composite Score
- average: 63.00

## Score Breakdown
- exact_match: 63.00
- f1: 71.27

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.040 | 0.002 | 0.012 |
| summarize_hop1 | 2.315 | 2.142 | 3.969 |
| query_hop2 | 1.059 | 1.016 | 1.446 |
| retrieve_hop2 | 0.445 | 0.002 | 1.563 |
| summarize_hop2 | 2.632 | 2.493 | 4.142 |
| answer | 1.047 | 0.986 | 1.649 |
| **Total** | **7.538** | **7.212** | **10.454** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 111 |
