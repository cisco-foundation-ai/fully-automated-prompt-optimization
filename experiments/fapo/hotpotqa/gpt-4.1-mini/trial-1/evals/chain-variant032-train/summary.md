# Evaluation Summary

Total cases: 150

## Composite Score
- average: 72.67

## Score Breakdown
- exact_match: 72.67
- f1: 79.17

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.050 | 0.003 | 0.035 |
| summarize_hop1 | 4.068 | 3.595 | 6.999 |
| query_hop2 | 2.104 | 1.879 | 3.828 |
| retrieve_hop2 | 0.338 | 0.002 | 1.531 |
| summarize_hop2 | 3.089 | 2.809 | 5.267 |
| answer | 2.446 | 1.865 | 4.956 |
| **Total** | **12.096** | **11.495** | **17.847** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 41 |
