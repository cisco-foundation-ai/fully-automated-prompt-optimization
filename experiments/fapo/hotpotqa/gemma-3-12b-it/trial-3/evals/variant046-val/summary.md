# Evaluation Summary

Total cases: 300

## Composite Score
- average: 58.33

## Score Breakdown
- exact_match: 58.33
- f1: 67.91

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.025 | 0.002 | 0.009 |
| summarize_hop1 | 2.244 | 2.094 | 3.601 |
| query_hop2 | 1.060 | 0.998 | 1.439 |
| retrieve_hop2 | 0.435 | 0.002 | 1.581 |
| summarize_hop2 | 3.360 | 3.184 | 5.476 |
| answer | 1.122 | 1.069 | 1.760 |
| **Total** | **8.246** | **7.851** | **11.956** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 125 |
