# Evaluation Summary

Total cases: 150

## Composite Score
- average: 71.33

## Score Breakdown
- exact_match: 71.33
- f1: 79.01

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.015 | 0.002 | 0.012 |
| summarize_hop1 | 5.059 | 4.430 | 9.217 |
| query_hop2 | 2.041 | 1.905 | 3.151 |
| retrieve_hop2 | 0.863 | 0.097 | 1.717 |
| summarize_hop2 | 2.700 | 2.494 | 4.384 |
| answer | 1.427 | 1.258 | 2.461 |
| **Total** | **12.104** | **11.238** | **20.414** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 43 |
