# Evaluation Summary

Total cases: 150

## Composite Score
- average: 70.67

## Score Breakdown
- exact_match: 70.67
- f1: 76.72

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.040 | 0.002 | 0.041 |
| summarize_hop1 | 3.129 | 2.529 | 4.687 |
| query_hop2 | 1.477 | 1.424 | 2.099 |
| retrieve_hop2 | 0.653 | 0.003 | 1.584 |
| summarize_hop2 | 2.349 | 2.192 | 3.876 |
| answer | 1.208 | 1.115 | 1.909 |
| **Total** | **8.855** | **7.910** | **13.084** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 44 |
