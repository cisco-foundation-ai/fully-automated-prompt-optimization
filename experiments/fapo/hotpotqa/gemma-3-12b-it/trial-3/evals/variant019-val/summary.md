# Evaluation Summary

Total cases: 300

## Composite Score
- average: 60.00

## Score Breakdown
- exact_match: 60.00
- f1: 69.46

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.026 | 0.002 | 0.012 |
| summarize_hop1 | 1.981 | 1.815 | 3.486 |
| query_hop2 | 1.017 | 0.982 | 1.420 |
| retrieve_hop2 | 0.517 | 0.003 | 1.618 |
| summarize_hop2 | 3.185 | 3.031 | 5.083 |
| answer | 1.108 | 1.034 | 1.702 |
| **Total** | **7.832** | **7.505** | **11.699** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 120 |
