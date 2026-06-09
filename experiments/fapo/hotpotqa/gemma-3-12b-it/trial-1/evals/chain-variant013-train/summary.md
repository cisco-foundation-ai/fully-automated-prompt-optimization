# Evaluation Summary

Total cases: 150

## Composite Score
- average: 62.67

## Score Breakdown
- exact_match: 62.67
- f1: 69.93

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.035 | 0.002 | 0.026 |
| summarize_hop1 | 2.335 | 2.152 | 4.194 |
| query_hop2 | 1.252 | 1.218 | 1.805 |
| retrieve_hop2 | 0.916 | 0.002 | 1.722 |
| summarize_hop2 | 2.208 | 2.106 | 3.244 |
| answer | 0.952 | 0.913 | 1.383 |
| **Total** | **7.698** | **7.027** | **12.410** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 56 |
