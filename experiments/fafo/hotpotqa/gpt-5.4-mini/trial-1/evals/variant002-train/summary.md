# Evaluation Summary

Total cases: 150

## Composite Score
- average: 49.33

## Score Breakdown
- exact_match: 49.33
- f1: 55.42

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.016 | 0.002 | 0.017 |
| summarize_hop1 | 1.176 | 1.089 | 1.914 |
| query_hop2 | 1.332 | 1.132 | 1.814 |
| retrieve_hop2 | 1.059 | 0.097 | 1.714 |
| summarize_hop2 | 1.235 | 1.063 | 1.712 |
| answer | 1.017 | 0.919 | 1.387 |
| **Total** | **5.834** | **5.162** | **13.330** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 76 |
