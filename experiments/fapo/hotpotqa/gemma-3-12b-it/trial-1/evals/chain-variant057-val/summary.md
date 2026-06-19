# Evaluation Summary

Total cases: 300

## Composite Score
- average: 63.00

## Score Breakdown
- exact_match: 63.00
- f1: 71.02

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 1.004 | 0.621 | 1.654 |
| summarize_hop1 | 2.261 | 2.144 | 3.902 |
| query_hop2 | 1.028 | 0.972 | 1.537 |
| retrieve_hop2 | 1.100 | 1.281 | 1.583 |
| summarize_hop2 | 2.471 | 2.404 | 3.797 |
| answer | 1.038 | 0.975 | 1.482 |
| **Total** | **8.902** | **8.796** | **12.477** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 111 |
