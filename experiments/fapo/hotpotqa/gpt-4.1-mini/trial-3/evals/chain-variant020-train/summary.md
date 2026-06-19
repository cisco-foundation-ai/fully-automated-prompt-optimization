# Evaluation Summary

Total cases: 150

## Composite Score
- average: 71.33

## Score Breakdown
- exact_match: 71.33
- f1: 77.66

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.044 | 0.002 | 0.040 |
| summarize_hop1 | 5.133 | 4.474 | 9.967 |
| query_hop2 | 2.206 | 2.029 | 3.507 |
| retrieve_hop2 | 0.565 | 0.086 | 1.634 |
| summarize_hop2 | 4.607 | 3.936 | 8.972 |
| answer | 1.726 | 1.503 | 2.734 |
| **Total** | **14.281** | **13.529** | **23.379** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 43 |
