# Evaluation Summary

Total cases: 111

## Composite Score
- average: 91.84

## Score Breakdown
- leakage_fraction: 0.08
- privacy: 91.78
- quality: 91.89
- quality_passed: 0.92

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 6.458 | 2.040 | 30.287 |
| call_untrusted | 7.121 | 4.297 | 20.518 |
| reconstruct_response | 6.995 | 4.889 | 20.022 |
| **Total** | **20.573** | **13.040** | **64.863** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 22 |
