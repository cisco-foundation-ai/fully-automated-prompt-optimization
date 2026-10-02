# Evaluation Summary

Total cases: 300

## Composite Score
- average: 68.00

## Score Breakdown
- exact_match: 68.00
- f1: 75.43

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.123 | 0.002 | 0.112 |
| summarize_hop1 | 1.347 | 1.279 | 2.077 |
| query_hop2 | 1.077 | 1.007 | 1.507 |
| retrieve_hop2 | 0.469 | 0.002 | 1.644 |
| summarize_hop2 | 1.166 | 1.063 | 1.733 |
| answer | 0.797 | 0.747 | 1.155 |
| **Total** | **4.979** | **4.376** | **6.751** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 96 |
