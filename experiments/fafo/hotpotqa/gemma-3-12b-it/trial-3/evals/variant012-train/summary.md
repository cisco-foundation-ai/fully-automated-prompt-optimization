# Evaluation Summary

Total cases: 150

## Composite Score
- average: 67.33

## Score Breakdown
- exact_match: 67.33
- f1: 74.54

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.072 | 0.002 | 0.036 |
| summarize_hop1 | 1.760 | 1.565 | 3.360 |
| query_hop2 | 0.991 | 0.944 | 1.333 |
| retrieve_hop2 | 0.836 | 0.003 | 1.652 |
| summarize_hop2 | 2.683 | 2.599 | 3.949 |
| answer | 0.973 | 0.906 | 1.436 |
| **Total** | **7.315** | **6.855** | **10.443** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 49 |
