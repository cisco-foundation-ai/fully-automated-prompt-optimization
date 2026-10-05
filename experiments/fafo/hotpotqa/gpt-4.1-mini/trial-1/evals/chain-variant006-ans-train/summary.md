# Evaluation Summary

Total cases: 150

## Composite Score
- average: 73.33

## Score Breakdown
- exact_match: 73.33
- f1: 79.41

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.016 | 0.002 | 0.010 |
| summarize_hop1 | 2.666 | 2.287 | 4.579 |
| query_hop2 | 1.595 | 1.457 | 2.556 |
| retrieve_hop2 | 0.798 | 0.093 | 1.671 |
| summarize_hop2 | 2.532 | 2.213 | 4.494 |
| answer | 1.473 | 1.357 | 2.500 |
| **Total** | **9.081** | **8.316** | **14.101** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 40 |
