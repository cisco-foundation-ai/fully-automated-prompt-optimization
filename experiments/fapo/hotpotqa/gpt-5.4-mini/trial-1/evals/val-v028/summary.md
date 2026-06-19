# Evaluation Summary

Total cases: 300

## Composite Score
- average: 67.00

## Score Breakdown
- exact_match: 67.00
- f1: 76.01

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.121 | 0.002 | 0.108 |
| summarize_hop1 | 1.245 | 1.122 | 2.020 |
| query_hop2 | 1.222 | 1.041 | 2.061 |
| retrieve_hop2 | 0.679 | 0.003 | 1.644 |
| summarize_hop2 | 1.665 | 1.433 | 2.230 |
| answer | 0.832 | 0.728 | 1.207 |
| **Total** | **5.763** | **4.973** | **10.172** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 99 |
