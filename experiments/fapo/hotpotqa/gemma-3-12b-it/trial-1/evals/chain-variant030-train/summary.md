# Evaluation Summary

Total cases: 150

## Composite Score
- average: 67.33

## Score Breakdown
- exact_match: 67.33
- f1: 72.55

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.100 | 0.003 | 0.063 |
| summarize_hop1 | 2.692 | 2.073 | 4.204 |
| query_hop2 | 1.277 | 1.238 | 1.825 |
| retrieve_hop2 | 0.457 | 0.002 | 1.573 |
| summarize_hop2 | 2.079 | 1.935 | 3.562 |
| answer | 0.975 | 0.925 | 1.407 |
| **Total** | **7.580** | **6.720** | **10.860** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 49 |
