# Evaluation Summary

Total cases: 300

## Composite Score
- average: 56.00

## Score Breakdown
- exact_match: 56.00
- f1: 66.48

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.021 | 0.002 | 0.011 |
| summarize_hop1 | 2.209 | 2.075 | 3.461 |
| query_hop2 | 1.014 | 0.988 | 1.420 |
| retrieve_hop2 | 0.654 | 0.002 | 1.637 |
| summarize_hop2 | 2.383 | 2.231 | 3.773 |
| answer | 1.116 | 1.050 | 1.660 |
| **Total** | **7.398** | **7.087** | **10.499** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 132 |
