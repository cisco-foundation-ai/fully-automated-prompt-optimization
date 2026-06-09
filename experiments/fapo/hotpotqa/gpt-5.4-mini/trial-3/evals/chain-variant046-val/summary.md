# Evaluation Summary

Total cases: 300

## Composite Score
- average: 72.33

## Score Breakdown
- exact_match: 72.33
- f1: 79.18

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.029 | 0.002 | 0.009 |
| summarize_hop1 | 1.396 | 1.293 | 1.961 |
| query_hop2 | 1.265 | 1.042 | 2.431 |
| retrieve_hop2 | 0.317 | 0.002 | 1.578 |
| summarize_hop2 | 1.441 | 1.306 | 1.975 |
| answer | 1.068 | 0.954 | 1.566 |
| **Total** | **5.517** | **4.874** | **8.501** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 83 |
