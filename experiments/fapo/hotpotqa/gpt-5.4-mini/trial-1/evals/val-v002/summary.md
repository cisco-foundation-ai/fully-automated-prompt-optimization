# Evaluation Summary

Total cases: 300

## Composite Score
- average: 63.00

## Score Breakdown
- exact_match: 63.00
- f1: 70.01

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.012 | 0.002 | 0.012 |
| summarize_hop1 | 1.215 | 1.087 | 1.729 |
| query_hop2 | 1.116 | 0.944 | 1.612 |
| retrieve_hop2 | 1.420 | 1.345 | 1.712 |
| summarize_hop2 | 1.090 | 1.034 | 1.508 |
| answer | 0.906 | 0.841 | 1.306 |
| **Total** | **5.759** | **5.232** | **8.363** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 111 |
