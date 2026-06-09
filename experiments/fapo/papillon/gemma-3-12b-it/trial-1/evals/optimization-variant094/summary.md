# Evaluation Summary

Total cases: 111

## Composite Score
- average: 96.60

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 96.79
- quality: 96.40
- quality_passed: 0.96

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.744 | 1.219 | 18.262 |
| call_untrusted | 15.832 | 15.419 | 28.003 |
| reconstruct_response | 16.497 | 16.285 | 27.967 |
| **Total** | **36.073** | **34.716** | **60.509** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 11 |
