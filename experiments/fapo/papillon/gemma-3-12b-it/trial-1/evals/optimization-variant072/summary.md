# Evaluation Summary

Total cases: 111

## Composite Score
- average: 97.57

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 96.94
- quality: 98.20
- quality_passed: 0.98

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.829 | 1.279 | 18.871 |
| call_untrusted | 15.799 | 15.791 | 26.045 |
| reconstruct_response | 16.610 | 16.525 | 29.296 |
| **Total** | **36.238** | **34.556** | **60.607** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 8 |
