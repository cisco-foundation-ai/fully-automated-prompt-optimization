# Evaluation Summary

Total cases: 300

## Composite Score
- average: 72.00

## Score Breakdown
- exact_match: 72.00
- f1: 78.65

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.050 | 0.002 | 0.009 |
| summarize_hop1 | 1.506 | 1.438 | 2.065 |
| query_hop2 | 1.061 | 0.952 | 1.482 |
| retrieve_hop2 | 0.583 | 0.002 | 1.675 |
| summarize_hop2 | 1.273 | 1.222 | 1.733 |
| answer | 0.964 | 0.882 | 1.244 |
| **Total** | **5.437** | **4.893** | **7.285** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 83 |
| query_hop2 | 1 |
