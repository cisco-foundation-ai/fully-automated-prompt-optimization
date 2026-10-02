# Evaluation Summary

Total cases: 150

## Composite Score
- average: 65.33

## Score Breakdown
- exact_match: 65.33
- f1: 71.02

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.074 | 0.003 | 0.051 |
| summarize_hop1 | 2.296 | 2.155 | 3.781 |
| query_hop2 | 1.275 | 1.247 | 1.847 |
| retrieve_hop2 | 0.612 | 0.006 | 1.703 |
| summarize_hop2 | 2.287 | 2.225 | 3.456 |
| answer | 1.000 | 0.950 | 1.372 |
| **Total** | **7.543** | **6.978** | **10.932** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 52 |
