# Evaluation Summary

Total cases: 111

## Composite Score
- average: 93.91

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 96.83
- quality: 90.99
- quality_passed: 0.91

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.602 | 1.202 | 17.656 |
| call_untrusted | 14.314 | 13.848 | 22.152 |
| reconstruct_response | 14.900 | 14.955 | 24.297 |
| **Total** | **32.816** | **31.480** | **55.108** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 16 |
