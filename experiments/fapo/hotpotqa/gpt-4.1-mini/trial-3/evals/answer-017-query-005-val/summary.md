# Evaluation Summary

Total cases: 300

## Composite Score
- average: 71.00

## Score Breakdown
- exact_match: 71.00
- f1: 78.76

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.003 | 0.002 | 0.004 |
| summarize_hop1 | 5.130 | 4.625 | 9.065 |
| query_hop2 | 2.906 | 2.506 | 5.069 |
| retrieve_hop2 | 1.595 | 1.506 | 1.628 |
| summarize_hop2 | 5.550 | 4.935 | 9.333 |
| answer | 1.916 | 1.740 | 3.084 |
| **Total** | **17.099** | **16.267** | **25.876** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 87 |
