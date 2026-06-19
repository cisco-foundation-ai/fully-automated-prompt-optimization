# Evaluation Summary

Total cases: 150

## Composite Score
- average: 69.33

## Score Breakdown
- exact_match: 69.33
- f1: 75.41

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 1.689 | 1.100 | 13.642 |
| summarize_hop1 | 1.375 | 1.258 | 2.314 |
| query_hop2 | 1.085 | 1.024 | 1.444 |
| retrieve_hop2 | 1.182 | 1.276 | 1.617 |
| summarize_hop2 | 1.730 | 1.563 | 3.435 |
| answer | 0.808 | 0.772 | 1.078 |
| **Total** | **7.870** | **6.909** | **20.541** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 46 |
