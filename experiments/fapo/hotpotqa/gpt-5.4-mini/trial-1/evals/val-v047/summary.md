# Evaluation Summary

Total cases: 300

## Composite Score
- average: 68.67

## Score Breakdown
- exact_match: 68.67
- f1: 77.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.113 | 0.002 | 0.106 |
| summarize_hop1 | 1.453 | 1.308 | 2.306 |
| query_hop2 | 1.193 | 1.075 | 1.814 |
| retrieve_hop2 | 0.376 | 0.002 | 1.603 |
| summarize_hop2 | 2.052 | 1.927 | 2.823 |
| answer | 0.843 | 0.749 | 1.220 |
| **Total** | **6.031** | **5.319** | **9.006** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 94 |
