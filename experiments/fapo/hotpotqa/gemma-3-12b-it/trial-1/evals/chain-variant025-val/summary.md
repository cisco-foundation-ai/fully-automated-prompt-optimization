# Evaluation Summary

Total cases: 300

## Composite Score
- average: 63.33

## Score Breakdown
- exact_match: 63.33
- f1: 71.09

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.028 | 0.002 | 0.010 |
| summarize_hop1 | 2.355 | 2.218 | 3.880 |
| query_hop2 | 1.053 | 1.027 | 1.464 |
| retrieve_hop2 | 0.668 | 0.003 | 1.628 |
| summarize_hop2 | 2.596 | 2.512 | 3.855 |
| answer | 1.053 | 1.012 | 1.525 |
| **Total** | **7.755** | **7.720** | **10.896** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 110 |
