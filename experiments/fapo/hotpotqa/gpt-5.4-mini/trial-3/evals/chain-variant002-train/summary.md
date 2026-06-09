# Evaluation Summary

Total cases: 150

## Composite Score
- average: 67.33

## Score Breakdown
- exact_match: 67.33
- f1: 74.48

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.091 | 0.002 | 0.066 |
| summarize_hop1 | 1.101 | 1.056 | 1.661 |
| query_hop2 | 0.959 | 0.913 | 1.306 |
| retrieve_hop2 | 0.681 | 0.002 | 1.728 |
| summarize_hop2 | 1.091 | 1.071 | 1.506 |
| answer | 0.844 | 0.812 | 1.161 |
| **Total** | **4.767** | **4.088** | **7.413** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 49 |
