# Evaluation Summary

Total cases: 150

## Composite Score
- average: 76.00

## Score Breakdown
- exact_match: 76.00
- f1: 79.52

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.095 | 0.002 | 0.074 |
| summarize_hop1 | 2.297 | 2.053 | 3.197 |
| query_hop2 | 1.183 | 1.065 | 1.549 |
| retrieve_hop2 | 0.710 | 0.004 | 1.695 |
| summarize_hop2 | 1.730 | 1.635 | 2.568 |
| answer | 1.090 | 0.790 | 1.349 |
| **Total** | **7.106** | **6.259** | **14.688** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 36 |
