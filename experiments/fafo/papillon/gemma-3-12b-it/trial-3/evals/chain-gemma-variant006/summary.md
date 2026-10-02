# Evaluation Summary

Total cases: 111

## Composite Score
- average: 95.86

## Score Breakdown
- leakage_fraction: 0.04
- privacy: 96.23
- quality: 95.50
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 10.625 | 1.733 | 23.370 |
| call_untrusted | 12.873 | 11.848 | 30.989 |
| reconstruct_response | 14.796 | 11.441 | 29.068 |
| **Total** | **38.294** | **27.082** | **106.718** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 12 |
