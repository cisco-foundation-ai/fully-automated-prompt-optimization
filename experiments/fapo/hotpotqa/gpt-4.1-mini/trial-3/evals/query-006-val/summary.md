# Evaluation Summary

Total cases: 300

## Composite Score
- average: 70.33

## Score Breakdown
- exact_match: 70.33
- f1: 78.64

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.021 | 0.002 | 0.007 |
| summarize_hop1 | 5.199 | 4.553 | 10.197 |
| query_hop2 | 2.318 | 2.016 | 4.194 |
| retrieve_hop2 | 1.147 | 1.496 | 1.602 |
| summarize_hop2 | 4.534 | 3.955 | 8.046 |
| answer | 1.707 | 1.550 | 2.901 |
| **Total** | **14.924** | **13.964** | **24.137** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 89 |
