# Evaluation Summary

Total cases: 300

## Composite Score
- average: 72.00

## Score Breakdown
- exact_match: 72.00
- f1: 79.38

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.038 | 0.002 | 0.009 |
| summarize_hop1 | 1.254 | 1.195 | 1.813 |
| query_hop2 | 1.030 | 0.972 | 1.437 |
| retrieve_hop2 | 0.433 | 0.002 | 1.579 |
| summarize_hop2 | 1.258 | 1.207 | 1.658 |
| answer | 0.930 | 0.875 | 1.385 |
| **Total** | **4.943** | **4.562** | **6.607** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 84 |
