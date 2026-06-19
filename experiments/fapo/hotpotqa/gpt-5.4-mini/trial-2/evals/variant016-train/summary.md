# Evaluation Summary

Total cases: 150

## Composite Score
- average: 69.33

## Score Breakdown
- exact_match: 69.33
- f1: 75.84

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.016 | 0.002 | 0.009 |
| summarize_hop1 | 2.046 | 1.996 | 2.990 |
| query_hop2 | 1.086 | 1.041 | 1.490 |
| retrieve_hop2 | 1.003 | 0.064 | 1.658 |
| summarize_hop2 | 1.497 | 1.439 | 2.198 |
| answer | 1.066 | 0.806 | 1.602 |
| **Total** | **6.713** | **6.041** | **9.182** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 46 |
