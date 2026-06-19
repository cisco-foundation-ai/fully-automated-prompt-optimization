# Evaluation Summary

Total cases: 150

## Composite Score
- average: 73.33

## Score Breakdown
- exact_match: 73.33
- f1: 78.77

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.018 | 0.002 | 0.009 |
| summarize_hop1 | 3.488 | 3.088 | 6.256 |
| query_hop2 | 2.199 | 1.950 | 4.048 |
| retrieve_hop2 | 0.925 | 0.255 | 1.711 |
| summarize_hop2 | 3.054 | 2.728 | 4.693 |
| answer | 1.403 | 1.267 | 2.193 |
| **Total** | **11.087** | **10.130** | **17.648** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 40 |
