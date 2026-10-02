# Evaluation Summary

Total cases: 150

## Composite Score
- average: 70.67

## Score Breakdown
- exact_match: 70.67
- f1: 74.82

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.058 | 0.002 | 0.048 |
| summarize_hop1 | 2.449 | 2.297 | 4.309 |
| query_hop2 | 1.028 | 0.998 | 1.457 |
| retrieve_hop2 | 0.522 | 0.003 | 1.574 |
| summarize_hop2 | 2.250 | 2.140 | 3.435 |
| answer | 0.959 | 0.928 | 1.426 |
| **Total** | **7.267** | **7.000** | **10.509** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 44 |
