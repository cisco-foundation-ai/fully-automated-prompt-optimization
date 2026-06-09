# Evaluation Summary

Total cases: 300

## Composite Score
- average: 62.33

## Score Breakdown
- exact_match: 62.33
- f1: 70.79

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.035 | 0.002 | 0.008 |
| summarize_hop1 | 2.352 | 2.188 | 3.818 |
| query_hop2 | 1.079 | 1.024 | 1.539 |
| retrieve_hop2 | 0.467 | 0.002 | 1.611 |
| summarize_hop2 | 2.687 | 2.599 | 3.960 |
| answer | 1.102 | 1.029 | 1.702 |
| **Total** | **7.723** | **7.371** | **11.241** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 113 |
