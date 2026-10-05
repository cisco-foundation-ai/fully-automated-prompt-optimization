# Evaluation Summary

Total cases: 300

## Composite Score
- average: 71.33

## Score Breakdown
- exact_match: 71.33
- f1: 78.08

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.039 | 0.002 | 0.009 |
| summarize_hop1 | 1.341 | 1.293 | 1.796 |
| query_hop2 | 1.017 | 0.972 | 1.475 |
| retrieve_hop2 | 0.680 | 0.005 | 1.593 |
| summarize_hop2 | 1.337 | 1.260 | 1.746 |
| answer | 0.976 | 0.913 | 1.540 |
| **Total** | **5.389** | **5.113** | **7.124** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 86 |
