# Evaluation Summary

Total cases: 150

## Composite Score
- average: 72.00

## Score Breakdown
- exact_match: 72.00
- f1: 80.13

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.020 | 0.002 | 0.009 |
| summarize_hop1 | 6.987 | 5.719 | 14.902 |
| query_hop2 | 3.047 | 2.738 | 5.500 |
| retrieve_hop2 | 0.785 | 0.003 | 1.622 |
| summarize_hop2 | 5.002 | 4.515 | 8.681 |
| answer | 2.240 | 1.960 | 3.727 |
| **Total** | **18.081** | **16.566** | **30.067** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 42 |
