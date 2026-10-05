# Evaluation Summary

Total cases: 150

## Composite Score
- average: 67.33

## Score Breakdown
- exact_match: 67.33
- f1: 75.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.029 | 0.002 | 0.014 |
| summarize_hop1 | 4.886 | 4.601 | 8.398 |
| query_hop2 | 1.242 | 1.151 | 2.003 |
| retrieve_hop2 | 0.684 | 0.002 | 1.600 |
| summarize_hop2 | 3.165 | 2.973 | 4.956 |
| answer | 1.012 | 0.952 | 1.573 |
| **Total** | **11.019** | **10.273** | **15.431** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 49 |
