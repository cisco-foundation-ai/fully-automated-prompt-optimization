# Evaluation Summary

Total cases: 111

## Composite Score
- average: 97.18

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 97.06
- quality: 97.30
- quality_passed: 0.97

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 4.307 | 1.458 | 17.944 |
| call_untrusted | 13.261 | 12.033 | 24.730 |
| reconstruct_response | 14.339 | 12.067 | 33.004 |
| **Total** | **31.907** | **28.730** | **70.374** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 8 |
