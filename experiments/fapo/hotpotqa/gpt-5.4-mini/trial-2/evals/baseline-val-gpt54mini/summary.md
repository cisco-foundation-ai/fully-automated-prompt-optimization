# Evaluation Summary

Total cases: 300

## Composite Score
- average: 44.67

## Score Breakdown
- exact_match: 44.67
- f1: 54.61

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.003 | 0.002 | 0.006 |
| summarize_hop1 | 1.335 | 1.042 | 1.856 |
| query_hop2 | 1.323 | 1.102 | 1.928 |
| retrieve_hop2 | 1.405 | 1.397 | 1.765 |
| summarize_hop2 | 1.224 | 1.054 | 1.760 |
| answer | 1.229 | 1.030 | 1.769 |
| **Total** | **6.520** | **5.744** | **18.036** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 166 |
