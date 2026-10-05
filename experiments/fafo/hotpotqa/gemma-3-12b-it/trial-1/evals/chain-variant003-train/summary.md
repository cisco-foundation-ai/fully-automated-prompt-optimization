# Evaluation Summary

Total cases: 150

## Composite Score
- average: 66.00

## Score Breakdown
- exact_match: 66.00
- f1: 74.12

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.018 | 0.002 | 0.012 |
| summarize_hop1 | 2.355 | 2.151 | 3.812 |
| query_hop2 | 1.032 | 1.010 | 1.420 |
| retrieve_hop2 | 1.387 | 1.563 | 1.666 |
| summarize_hop2 | 2.499 | 2.479 | 3.500 |
| answer | 0.813 | 0.797 | 1.200 |
| **Total** | **8.103** | **7.820** | **11.654** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 51 |
