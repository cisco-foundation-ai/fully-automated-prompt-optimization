# Evaluation Summary

Total cases: 150

## Composite Score
- average: 66.00

## Score Breakdown
- exact_match: 66.00
- f1: 72.84

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.029 | 0.002 | 0.013 |
| summarize_hop1 | 2.367 | 2.191 | 4.265 |
| query_hop2 | 1.083 | 1.038 | 1.648 |
| retrieve_hop2 | 1.456 | 1.306 | 1.664 |
| summarize_hop2 | 3.228 | 2.993 | 5.270 |
| answer | 1.124 | 1.077 | 1.674 |
| **Total** | **9.286** | **8.831** | **13.618** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 51 |
