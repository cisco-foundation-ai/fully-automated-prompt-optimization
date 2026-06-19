# Evaluation Summary

Total cases: 221

## Composite Score
- average: 94.73

## Score Breakdown
- leakage_fraction: 0.07
- privacy: 93.08
- quality: 96.38
- quality_passed: 0.96

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 8.803 | 1.614 | 17.288 |
| call_untrusted | 13.838 | 13.252 | 22.980 |
| reconstruct_response | 13.354 | 13.203 | 25.020 |
| **Total** | **35.995** | **28.396** | **70.239** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 28 |
