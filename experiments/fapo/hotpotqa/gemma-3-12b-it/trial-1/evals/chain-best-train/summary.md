# Evaluation Summary

Total cases: 150

## Composite Score
- average: 71.33

## Score Breakdown
- exact_match: 71.33
- f1: 77.52

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.077 | 0.003 | 0.051 |
| summarize_hop1 | 2.403 | 2.159 | 4.584 |
| query_hop2 | 1.029 | 1.000 | 1.369 |
| retrieve_hop2 | 0.389 | 0.002 | 1.574 |
| summarize_hop2 | 2.508 | 2.400 | 3.774 |
| answer | 1.041 | 0.998 | 1.524 |
| **Total** | **7.446** | **7.031** | **10.626** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 43 |
