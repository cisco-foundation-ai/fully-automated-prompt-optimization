# Evaluation Summary

Total cases: 111

## Composite Score
- average: 93.72

## Score Breakdown
- leakage_fraction: 0.05
- privacy: 94.65
- quality: 92.79
- quality_passed: 0.93

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 4.526 | 1.431 | 22.232 |
| call_untrusted | 12.642 | 11.861 | 24.856 |
| reconstruct_response | 12.379 | 11.671 | 23.035 |
| **Total** | **29.547** | **26.383** | **57.743** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 16 |
