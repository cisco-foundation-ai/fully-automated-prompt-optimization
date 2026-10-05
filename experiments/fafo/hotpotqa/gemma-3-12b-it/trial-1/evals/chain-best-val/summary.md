# Evaluation Summary

Total cases: 300

## Composite Score
- average: 65.00

## Score Breakdown
- exact_match: 65.00
- f1: 73.11

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.034 | 0.003 | 0.012 |
| summarize_hop1 | 2.339 | 2.153 | 4.092 |
| query_hop2 | 1.032 | 0.981 | 1.480 |
| retrieve_hop2 | 0.322 | 0.002 | 1.116 |
| summarize_hop2 | 2.803 | 2.460 | 4.070 |
| answer | 1.051 | 0.994 | 1.559 |
| **Total** | **7.582** | **7.030** | **10.998** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 105 |
