# Evaluation Summary

Total cases: 150

## Composite Score
- average: 75.33

## Score Breakdown
- exact_match: 75.33
- f1: 82.01

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.055 | 0.002 | 0.036 |
| summarize_hop1 | 1.426 | 1.366 | 1.904 |
| query_hop2 | 1.277 | 1.058 | 1.707 |
| retrieve_hop2 | 0.860 | 0.099 | 1.630 |
| summarize_hop2 | 1.367 | 1.268 | 1.946 |
| answer | 0.965 | 0.869 | 1.266 |
| **Total** | **5.950** | **5.546** | **8.368** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 37 |
