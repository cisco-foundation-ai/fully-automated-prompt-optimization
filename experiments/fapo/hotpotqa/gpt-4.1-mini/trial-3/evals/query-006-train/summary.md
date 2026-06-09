# Evaluation Summary

Total cases: 150

## Composite Score
- average: 77.33

## Score Breakdown
- exact_match: 77.33
- f1: 82.13

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.034 | 0.002 | 0.021 |
| summarize_hop1 | 4.837 | 3.766 | 6.983 |
| query_hop2 | 3.598 | 2.793 | 7.547 |
| retrieve_hop2 | 1.212 | 1.256 | 1.608 |
| summarize_hop2 | 4.639 | 4.310 | 7.569 |
| answer | 1.617 | 1.416 | 2.728 |
| **Total** | **15.937** | **14.393** | **25.449** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 34 |
