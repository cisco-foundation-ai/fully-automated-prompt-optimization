# Evaluation Summary

Total cases: 150

## Composite Score
- average: 69.33

## Score Breakdown
- exact_match: 69.33
- f1: 77.21

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.017 | 0.002 | 0.010 |
| summarize_hop1 | 2.943 | 2.550 | 5.793 |
| query_hop2 | 1.853 | 1.668 | 3.131 |
| retrieve_hop2 | 1.136 | 1.082 | 1.675 |
| summarize_hop2 | 2.530 | 2.158 | 4.563 |
| answer | 1.306 | 1.153 | 2.168 |
| **Total** | **9.785** | **9.043** | **16.864** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 46 |
