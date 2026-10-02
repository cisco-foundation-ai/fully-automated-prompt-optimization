# Evaluation Summary

Total cases: 300

## Composite Score
- average: 68.33

## Score Breakdown
- exact_match: 68.33
- f1: 75.75

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.031 | 0.002 | 0.010 |
| summarize_hop1 | 3.843 | 3.471 | 7.091 |
| query_hop2 | 1.769 | 1.614 | 3.104 |
| retrieve_hop2 | 0.433 | 0.003 | 1.600 |
| summarize_hop2 | 3.565 | 3.172 | 6.035 |
| answer | 1.656 | 1.554 | 2.523 |
| **Total** | **11.297** | **10.797** | **16.391** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 95 |
