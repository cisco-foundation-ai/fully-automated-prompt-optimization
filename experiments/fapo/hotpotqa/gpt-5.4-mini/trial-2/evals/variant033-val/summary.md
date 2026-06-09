# Evaluation Summary

Total cases: 300

## Composite Score
- average: 71.33

## Score Breakdown
- exact_match: 71.33
- f1: 78.80

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.033 | 0.002 | 0.008 |
| summarize_hop1 | 2.115 | 1.855 | 3.069 |
| query_hop2 | 1.214 | 1.059 | 1.774 |
| retrieve_hop2 | 0.637 | 0.084 | 1.386 |
| summarize_hop2 | 1.660 | 1.545 | 2.468 |
| answer | 1.003 | 0.799 | 2.064 |
| **Total** | **6.662** | **6.157** | **9.823** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 86 |
