# Evaluation Summary

Total cases: 150

## Composite Score
- average: 71.33

## Score Breakdown
- exact_match: 71.33
- f1: 77.08

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.061 | 0.002 | 0.035 |
| summarize_hop1 | 2.435 | 2.224 | 4.027 |
| query_hop2 | 1.038 | 0.998 | 1.408 |
| retrieve_hop2 | 0.544 | 0.002 | 1.571 |
| summarize_hop2 | 2.303 | 2.189 | 3.529 |
| answer | 0.962 | 0.920 | 1.368 |
| **Total** | **7.343** | **6.921** | **11.475** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 43 |
