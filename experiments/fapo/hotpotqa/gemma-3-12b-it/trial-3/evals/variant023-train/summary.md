# Evaluation Summary

Total cases: 150

## Composite Score
- average: 70.00

## Score Breakdown
- exact_match: 70.00
- f1: 75.48

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.084 | 0.002 | 0.053 |
| summarize_hop1 | 2.293 | 2.125 | 3.864 |
| query_hop2 | 1.007 | 0.989 | 1.305 |
| retrieve_hop2 | 0.640 | 0.003 | 1.647 |
| summarize_hop2 | 3.501 | 3.423 | 5.707 |
| answer | 1.120 | 1.007 | 1.863 |
| **Total** | **8.645** | **8.334** | **12.354** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 45 |
