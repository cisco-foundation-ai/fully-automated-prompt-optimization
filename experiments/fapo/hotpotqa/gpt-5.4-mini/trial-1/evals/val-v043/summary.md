# Evaluation Summary

Total cases: 300

## Composite Score
- average: 71.33

## Score Breakdown
- exact_match: 71.33
- f1: 78.59

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.098 | 0.002 | 0.106 |
| summarize_hop1 | 1.403 | 1.312 | 2.117 |
| query_hop2 | 1.219 | 1.102 | 2.062 |
| retrieve_hop2 | 0.675 | 0.003 | 1.600 |
| summarize_hop2 | 1.633 | 1.591 | 2.381 |
| answer | 0.793 | 0.739 | 1.219 |
| **Total** | **5.821** | **5.191** | **8.074** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 85 |
| query_hop2 | 1 |
