# Evaluation Summary

Total cases: 150

## Composite Score
- average: 65.33

## Score Breakdown
- exact_match: 65.33
- f1: 71.30

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.054 | 0.002 | 0.040 |
| summarize_hop1 | 2.427 | 2.235 | 3.870 |
| query_hop2 | 1.321 | 1.293 | 1.856 |
| retrieve_hop2 | 0.680 | 0.002 | 1.657 |
| summarize_hop2 | 2.364 | 2.301 | 3.539 |
| answer | 0.711 | 0.669 | 1.013 |
| **Total** | **7.557** | **7.005** | **11.503** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 52 |
