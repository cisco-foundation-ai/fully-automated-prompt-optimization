# Evaluation Summary

Total cases: 150

## Composite Score
- average: 72.67

## Score Breakdown
- exact_match: 72.67
- f1: 79.93

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.028 | 0.002 | 0.009 |
| summarize_hop1 | 1.455 | 1.348 | 2.200 |
| query_hop2 | 0.950 | 0.891 | 1.418 |
| retrieve_hop2 | 0.928 | 0.004 | 1.684 |
| summarize_hop2 | 1.231 | 1.127 | 1.929 |
| answer | 0.919 | 0.895 | 1.201 |
| **Total** | **5.510** | **5.005** | **7.677** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 41 |
