# Evaluation Summary

Total cases: 150

## Composite Score
- average: 48.67

## Score Breakdown
- exact_match: 48.67
- f1: 53.23

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.004 | 0.002 | 0.009 |
| summarize_hop1 | 1.350 | 1.308 | 1.820 |
| query_hop2 | 1.226 | 1.179 | 1.698 |
| retrieve_hop2 | 1.520 | 1.130 | 1.766 |
| summarize_hop2 | 1.418 | 1.359 | 1.986 |
| answer | 1.018 | 0.891 | 1.982 |
| **Total** | **6.535** | **6.085** | **8.983** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 77 |
