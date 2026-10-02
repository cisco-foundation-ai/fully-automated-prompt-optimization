# Evaluation Summary

Total cases: 150

## Composite Score
- average: 75.33

## Score Breakdown
- exact_match: 75.33
- f1: 81.62

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.077 | 0.002 | 0.041 |
| summarize_hop1 | 1.430 | 1.368 | 1.932 |
| query_hop2 | 0.982 | 0.956 | 1.337 |
| retrieve_hop2 | 0.487 | 0.002 | 1.736 |
| summarize_hop2 | 1.286 | 1.208 | 1.765 |
| answer | 0.883 | 0.845 | 1.178 |
| **Total** | **5.144** | **4.618** | **7.285** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 37 |
