# Evaluation Summary

Total cases: 150

## Composite Score
- average: 71.33

## Score Breakdown
- exact_match: 71.33
- f1: 77.39

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.049 | 0.002 | 0.046 |
| summarize_hop1 | 2.828 | 2.462 | 5.383 |
| query_hop2 | 1.565 | 1.458 | 2.351 |
| retrieve_hop2 | 0.612 | 0.002 | 1.589 |
| summarize_hop2 | 2.711 | 2.301 | 4.355 |
| answer | 1.509 | 1.417 | 2.377 |
| **Total** | **9.273** | **8.511** | **13.900** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 43 |
