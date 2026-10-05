# Evaluation Summary

Total cases: 300

## Composite Score
- average: 64.00

## Score Breakdown
- exact_match: 64.00
- f1: 71.06

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.042 | 0.002 | 0.016 |
| summarize_hop1 | 2.339 | 2.159 | 3.924 |
| query_hop2 | 1.078 | 0.994 | 1.459 |
| retrieve_hop2 | 0.383 | 0.002 | 1.586 |
| summarize_hop2 | 2.632 | 2.550 | 3.932 |
| answer | 0.718 | 0.668 | 1.080 |
| **Total** | **7.191** | **6.896** | **11.101** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 108 |
