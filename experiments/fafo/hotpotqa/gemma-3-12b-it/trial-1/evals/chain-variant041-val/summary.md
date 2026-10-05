# Evaluation Summary

Total cases: 300

## Composite Score
- average: 61.00

## Score Breakdown
- exact_match: 61.00
- f1: 69.68

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.032 | 0.002 | 0.013 |
| summarize_hop1 | 2.330 | 2.143 | 4.074 |
| query_hop2 | 1.033 | 0.994 | 1.510 |
| retrieve_hop2 | 0.533 | 0.002 | 1.590 |
| summarize_hop2 | 2.234 | 2.128 | 3.577 |
| answer | 1.027 | 0.974 | 1.499 |
| **Total** | **7.188** | **6.946** | **10.380** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 117 |
