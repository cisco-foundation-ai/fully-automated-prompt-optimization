# Evaluation Summary

Total cases: 300

## Composite Score
- average: 62.67

## Score Breakdown
- exact_match: 62.67
- f1: 70.09

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.019 | 0.002 | 0.012 |
| summarize_hop1 | 2.355 | 2.155 | 3.964 |
| query_hop2 | 1.043 | 1.010 | 1.428 |
| retrieve_hop2 | 0.700 | 0.005 | 1.625 |
| summarize_hop2 | 2.269 | 2.098 | 3.495 |
| answer | 0.989 | 0.938 | 1.411 |
| **Total** | **7.375** | **7.211** | **10.635** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 112 |
