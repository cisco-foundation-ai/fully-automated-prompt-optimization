# Evaluation Summary

Total cases: 300

## Composite Score
- average: 67.33

## Score Breakdown
- exact_match: 67.33
- f1: 75.14

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.042 | 0.002 | 0.014 |
| summarize_hop1 | 2.233 | 2.151 | 3.225 |
| query_hop2 | 1.160 | 1.099 | 1.728 |
| retrieve_hop2 | 0.358 | 0.002 | 1.350 |
| summarize_hop2 | 1.849 | 1.562 | 2.161 |
| answer | 0.895 | 0.782 | 1.381 |
| **Total** | **6.537** | **5.917** | **9.305** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 98 |
