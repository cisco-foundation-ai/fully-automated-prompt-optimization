# Evaluation Summary

Total cases: 150

## Composite Score
- average: 74.00

## Score Breakdown
- exact_match: 74.00
- f1: 81.66

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.026 | 0.002 | 0.022 |
| summarize_hop1 | 4.287 | 3.950 | 7.418 |
| query_hop2 | 2.571 | 1.911 | 2.863 |
| retrieve_hop2 | 0.508 | 0.002 | 1.587 |
| summarize_hop2 | 5.044 | 4.556 | 9.053 |
| answer | 1.567 | 1.453 | 2.486 |
| **Total** | **14.003** | **12.861** | **21.757** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 39 |
