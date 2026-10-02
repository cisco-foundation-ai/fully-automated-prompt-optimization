# Evaluation Summary

Total cases: 111

## Composite Score
- average: 95.77

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 96.94
- quality: 94.59
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.528 | 1.196 | 17.748 |
| call_untrusted | 14.553 | 15.140 | 24.010 |
| reconstruct_response | 15.357 | 15.812 | 26.789 |
| **Total** | **33.438** | **32.799** | **59.538** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 13 |
