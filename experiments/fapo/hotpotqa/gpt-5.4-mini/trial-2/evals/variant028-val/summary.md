# Evaluation Summary

Total cases: 300

## Composite Score
- average: 65.33

## Score Breakdown
- exact_match: 65.33
- f1: 72.35

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.038 | 0.002 | 0.011 |
| summarize_hop1 | 2.284 | 2.180 | 3.257 |
| query_hop2 | 1.199 | 1.115 | 1.583 |
| retrieve_hop2 | 0.366 | 0.002 | 1.586 |
| summarize_hop2 | 1.796 | 1.718 | 2.574 |
| answer | 0.868 | 0.804 | 1.339 |
| **Total** | **6.550** | **6.162** | **8.951** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 104 |
