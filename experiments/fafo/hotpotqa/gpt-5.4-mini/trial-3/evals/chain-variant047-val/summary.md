# Evaluation Summary

Total cases: 300

## Composite Score
- average: 71.00

## Score Breakdown
- exact_match: 71.00
- f1: 77.44

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.047 | 0.002 | 0.012 |
| summarize_hop1 | 1.456 | 1.228 | 1.912 |
| query_hop2 | 1.165 | 1.030 | 2.077 |
| retrieve_hop2 | 0.301 | 0.002 | 1.519 |
| summarize_hop2 | 1.434 | 1.292 | 2.080 |
| answer | 1.027 | 0.950 | 1.456 |
| **Total** | **5.430** | **4.802** | **8.141** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 87 |
