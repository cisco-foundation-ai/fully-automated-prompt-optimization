# Evaluation Summary

Total cases: 300

## Composite Score
- average: 66.33

## Score Breakdown
- exact_match: 66.33
- f1: 75.61

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.017 | 0.002 | 0.008 |
| summarize_hop1 | 5.573 | 4.810 | 11.497 |
| query_hop2 | 3.014 | 2.672 | 5.280 |
| retrieve_hop2 | 0.774 | 1.030 | 1.559 |
| summarize_hop2 | 4.662 | 4.367 | 7.544 |
| answer | 2.192 | 2.038 | 3.634 |
| **Total** | **16.232** | **15.096** | **26.175** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 100 |
| query_hop2 | 1 |
