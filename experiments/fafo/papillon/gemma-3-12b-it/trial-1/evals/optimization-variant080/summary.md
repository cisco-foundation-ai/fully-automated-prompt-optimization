# Evaluation Summary

Total cases: 111

## Composite Score
- average: 97.92

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 96.74
- quality: 99.10
- quality_passed: 0.99

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.592 | 1.330 | 16.700 |
| call_untrusted | 15.223 | 14.991 | 25.054 |
| reconstruct_response | 15.430 | 15.210 | 24.707 |
| **Total** | **34.246** | **33.357** | **56.374** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 8 |
