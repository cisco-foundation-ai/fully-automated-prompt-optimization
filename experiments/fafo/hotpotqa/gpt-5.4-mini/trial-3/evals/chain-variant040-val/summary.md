# Evaluation Summary

Total cases: 300

## Composite Score
- average: 70.33

## Score Breakdown
- exact_match: 70.33
- f1: 76.91

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.028 | 0.002 | 0.008 |
| summarize_hop1 | 1.330 | 1.264 | 1.962 |
| query_hop2 | 1.189 | 1.012 | 1.884 |
| retrieve_hop2 | 0.328 | 0.002 | 1.134 |
| summarize_hop2 | 1.414 | 1.281 | 2.114 |
| answer | 0.931 | 0.833 | 1.373 |
| **Total** | **5.220** | **4.612** | **8.513** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 89 |
