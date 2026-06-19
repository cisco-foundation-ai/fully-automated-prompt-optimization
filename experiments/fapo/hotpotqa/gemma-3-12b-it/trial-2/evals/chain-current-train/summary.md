# Evaluation Summary

Total cases: 150

## Composite Score
- average: 72.00

## Score Breakdown
- exact_match: 72.00
- f1: 76.89

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.026 | 0.003 | 0.017 |
| summarize_hop1 | 3.426 | 3.268 | 5.932 |
| query_hop2 | 1.165 | 1.119 | 1.598 |
| retrieve_hop2 | 0.544 | 0.002 | 1.600 |
| summarize_hop2 | 3.087 | 2.890 | 4.562 |
| answer | 0.974 | 0.931 | 1.316 |
| **Total** | **9.222** | **8.630** | **13.147** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 42 |
