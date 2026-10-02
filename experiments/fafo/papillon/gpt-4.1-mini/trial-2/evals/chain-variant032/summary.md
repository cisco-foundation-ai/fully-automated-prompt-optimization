# Evaluation Summary

Total cases: 111

## Composite Score
- average: 94.53

## Score Breakdown
- leakage_fraction: 0.04
- privacy: 96.27
- quality: 92.79
- quality_passed: 0.93

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 7.588 | 3.300 | 35.413 |
| call_untrusted | 8.919 | 4.999 | 29.867 |
| reconstruct_response | 8.704 | 4.264 | 27.932 |
| **Total** | **25.210** | **14.157** | **79.903** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 14 |
