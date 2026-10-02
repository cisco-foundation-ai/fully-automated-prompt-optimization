# Evaluation Summary

Total cases: 300

## Composite Score
- average: 40.67

## Score Breakdown
- exact_match: 40.67
- f1: 55.09

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.003 | 0.002 | 0.008 |
| summarize_hop1 | 4.737 | 3.954 | 8.825 |
| query_hop2 | 3.063 | 2.481 | 5.822 |
| retrieve_hop2 | 1.099 | 1.139 | 1.641 |
| summarize_hop2 | 3.245 | 2.787 | 6.245 |
| answer | 2.738 | 2.220 | 6.058 |
| **Total** | **14.887** | **13.514** | **24.973** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 178 |
