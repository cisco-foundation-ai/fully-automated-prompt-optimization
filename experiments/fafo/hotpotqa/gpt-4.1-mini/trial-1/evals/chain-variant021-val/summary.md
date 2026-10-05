# Evaluation Summary

Total cases: 300

## Composite Score
- average: 68.00

## Score Breakdown
- exact_match: 68.00
- f1: 75.53

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.022 | 0.002 | 0.007 |
| summarize_hop1 | 2.963 | 2.489 | 5.185 |
| query_hop2 | 1.601 | 1.502 | 2.322 |
| retrieve_hop2 | 1.043 | 1.077 | 1.635 |
| summarize_hop2 | 2.915 | 2.719 | 4.617 |
| answer | 1.476 | 1.359 | 2.062 |
| **Total** | **10.020** | **9.558** | **13.938** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 96 |
