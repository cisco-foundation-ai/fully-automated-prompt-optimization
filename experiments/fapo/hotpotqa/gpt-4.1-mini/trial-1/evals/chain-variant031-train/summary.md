# Evaluation Summary

Total cases: 150

## Composite Score
- average: 75.33

## Score Breakdown
- exact_match: 75.33
- f1: 81.39

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.043 | 0.002 | 0.027 |
| summarize_hop1 | 4.049 | 3.546 | 7.785 |
| query_hop2 | 2.154 | 1.985 | 3.821 |
| retrieve_hop2 | 0.444 | 0.002 | 1.573 |
| summarize_hop2 | 3.725 | 3.270 | 6.358 |
| answer | 1.876 | 1.699 | 3.263 |
| **Total** | **12.291** | **11.598** | **20.147** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 37 |
