# Evaluation Summary

Total cases: 150

## Composite Score
- average: 61.33

## Score Breakdown
- exact_match: 61.33
- f1: 70.93

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.040 | 0.002 | 0.012 |
| summarize_hop1 | 2.425 | 2.149 | 4.306 |
| query_hop2 | 1.037 | 0.958 | 1.442 |
| retrieve_hop2 | 1.414 | 1.251 | 1.675 |
| summarize_hop2 | 2.545 | 2.547 | 3.629 |
| answer | 0.859 | 0.825 | 1.287 |
| **Total** | **8.320** | **7.884** | **11.160** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 58 |
