# Evaluation Summary

Total cases: 300

## Composite Score
- average: 71.00

## Score Breakdown
- exact_match: 71.00
- f1: 77.27

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.059 | 0.002 | 0.009 |
| summarize_hop1 | 1.218 | 1.187 | 1.782 |
| query_hop2 | 1.017 | 0.956 | 1.383 |
| retrieve_hop2 | 0.433 | 0.002 | 1.630 |
| summarize_hop2 | 1.276 | 1.188 | 1.907 |
| answer | 0.910 | 0.863 | 1.300 |
| **Total** | **4.912** | **4.509** | **6.755** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 87 |
