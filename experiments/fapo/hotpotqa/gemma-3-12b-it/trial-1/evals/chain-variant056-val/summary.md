# Evaluation Summary

Total cases: 300

## Composite Score
- average: 62.00

## Score Breakdown
- exact_match: 62.00
- f1: 69.78

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.033 | 0.002 | 0.012 |
| summarize_hop1 | 2.327 | 2.170 | 3.709 |
| query_hop2 | 1.042 | 0.972 | 1.463 |
| retrieve_hop2 | 0.363 | 0.002 | 1.330 |
| summarize_hop2 | 2.606 | 2.507 | 4.126 |
| answer | 1.059 | 0.997 | 1.574 |
| **Total** | **7.430** | **7.098** | **10.765** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 114 |
