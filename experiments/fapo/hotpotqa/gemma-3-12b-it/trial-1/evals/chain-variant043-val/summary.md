# Evaluation Summary

Total cases: 300

## Composite Score
- average: 63.00

## Score Breakdown
- exact_match: 63.00
- f1: 69.83

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.033 | 0.002 | 0.014 |
| summarize_hop1 | 2.435 | 2.166 | 4.321 |
| query_hop2 | 2.092 | 1.022 | 1.595 |
| retrieve_hop2 | 0.605 | 0.007 | 1.628 |
| summarize_hop2 | 2.642 | 2.495 | 4.298 |
| answer | 1.122 | 0.999 | 1.770 |
| **Total** | **8.930** | **7.540** | **11.600** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 111 |
