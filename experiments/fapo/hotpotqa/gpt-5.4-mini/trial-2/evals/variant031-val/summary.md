# Evaluation Summary

Total cases: 300

## Composite Score
- average: 69.00

## Score Breakdown
- exact_match: 69.00
- f1: 77.32

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.053 | 0.002 | 0.012 |
| summarize_hop1 | 2.409 | 2.240 | 3.445 |
| query_hop2 | 1.385 | 1.164 | 1.975 |
| retrieve_hop2 | 0.319 | 0.002 | 1.595 |
| summarize_hop2 | 1.780 | 1.642 | 2.515 |
| answer | 0.952 | 0.798 | 1.499 |
| **Total** | **6.899** | **6.264** | **10.002** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 93 |
