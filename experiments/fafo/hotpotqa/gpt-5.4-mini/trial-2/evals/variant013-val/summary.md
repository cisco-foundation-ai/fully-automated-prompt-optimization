# Evaluation Summary

Total cases: 300

## Composite Score
- average: 68.33

## Score Breakdown
- exact_match: 68.33
- f1: 74.40

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.028 | 0.002 | 0.007 |
| summarize_hop1 | 2.215 | 2.065 | 3.227 |
| query_hop2 | 1.157 | 1.047 | 1.498 |
| retrieve_hop2 | 0.620 | 0.003 | 1.616 |
| summarize_hop2 | 1.706 | 1.602 | 2.558 |
| answer | 0.841 | 0.780 | 1.193 |
| **Total** | **6.567** | **6.085** | **9.191** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 95 |
