# Evaluation Summary

Total cases: 300

## Composite Score
- average: 58.33

## Score Breakdown
- exact_match: 58.33
- f1: 67.49

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 1.025 | 0.615 | 1.716 |
| summarize_hop1 | 2.283 | 2.119 | 3.871 |
| query_hop2 | 1.026 | 0.998 | 1.419 |
| retrieve_hop2 | 1.174 | 1.323 | 1.666 |
| summarize_hop2 | 2.557 | 2.450 | 3.756 |
| answer | 0.848 | 0.823 | 1.148 |
| **Total** | **8.913** | **8.729** | **12.219** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 125 |
