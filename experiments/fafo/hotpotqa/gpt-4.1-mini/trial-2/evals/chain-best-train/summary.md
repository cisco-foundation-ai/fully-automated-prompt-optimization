# Evaluation Summary

Total cases: 150

## Composite Score
- average: 41.33

## Score Breakdown
- exact_match: 41.33
- f1: 55.32

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 1.303 | 1.311 | 1.656 |
| summarize_hop1 | 3.848 | 3.377 | 7.192 |
| query_hop2 | 1.990 | 1.751 | 3.378 |
| retrieve_hop2 | 0.905 | 1.317 | 1.628 |
| summarize_hop2 | 2.587 | 2.441 | 3.927 |
| answer | 1.843 | 1.644 | 3.029 |
| **Total** | **12.477** | **11.584** | **18.444** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 88 |
