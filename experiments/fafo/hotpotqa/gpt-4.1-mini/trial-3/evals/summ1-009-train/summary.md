# Evaluation Summary

Total cases: 150

## Composite Score
- average: 75.33

## Score Breakdown
- exact_match: 75.33
- f1: 81.84

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.016 | 0.002 | 0.010 |
| summarize_hop1 | 9.023 | 7.590 | 16.253 |
| query_hop2 | 2.753 | 2.505 | 4.498 |
| retrieve_hop2 | 1.011 | 0.005 | 1.621 |
| summarize_hop2 | 5.257 | 4.936 | 8.733 |
| answer | 2.057 | 1.796 | 4.017 |
| **Total** | **20.118** | **18.197** | **31.860** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 37 |
