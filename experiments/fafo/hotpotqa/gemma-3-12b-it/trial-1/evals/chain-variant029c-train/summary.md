# Evaluation Summary

Total cases: 150

## Composite Score
- average: 66.67

## Score Breakdown
- exact_match: 66.67
- f1: 74.32

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.062 | 0.003 | 0.062 |
| summarize_hop1 | 2.381 | 2.277 | 3.954 |
| query_hop2 | 1.029 | 0.978 | 1.366 |
| retrieve_hop2 | 0.473 | 0.002 | 1.113 |
| summarize_hop2 | 2.311 | 2.140 | 3.600 |
| answer | 1.010 | 0.961 | 1.444 |
| **Total** | **7.265** | **6.835** | **11.277** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 50 |
