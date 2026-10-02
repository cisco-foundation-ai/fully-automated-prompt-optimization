# Evaluation Summary

Total cases: 150

## Composite Score
- average: 76.00

## Score Breakdown
- exact_match: 76.00
- f1: 81.92

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.073 | 0.002 | 0.064 |
| summarize_hop1 | 1.414 | 1.337 | 1.947 |
| query_hop2 | 1.049 | 0.962 | 1.829 |
| retrieve_hop2 | 0.930 | 1.056 | 1.578 |
| summarize_hop2 | 1.246 | 1.188 | 1.749 |
| answer | 0.968 | 0.853 | 1.963 |
| **Total** | **5.679** | **5.348** | **8.054** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 36 |
