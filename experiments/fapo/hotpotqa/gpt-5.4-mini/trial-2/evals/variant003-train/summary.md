# Evaluation Summary

Total cases: 150

## Composite Score
- average: 64.00

## Score Breakdown
- exact_match: 64.00
- f1: 72.29

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.056 | 0.002 | 0.047 |
| summarize_hop1 | 1.206 | 1.079 | 2.126 |
| query_hop2 | 0.967 | 0.922 | 1.337 |
| retrieve_hop2 | 0.823 | 0.003 | 1.753 |
| summarize_hop2 | 1.204 | 1.059 | 1.617 |
| answer | 0.945 | 0.827 | 1.951 |
| **Total** | **5.201** | **4.543** | **8.413** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 54 |
