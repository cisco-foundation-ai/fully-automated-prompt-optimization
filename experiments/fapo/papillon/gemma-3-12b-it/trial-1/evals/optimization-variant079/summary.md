# Evaluation Summary

Total cases: 111

## Composite Score
- average: 94.47

## Score Breakdown
- leakage_fraction: 0.04
- privacy: 96.16
- quality: 92.79
- quality_passed: 0.93

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.808 | 1.322 | 19.231 |
| call_untrusted | 16.101 | 15.626 | 31.394 |
| reconstruct_response | 16.420 | 15.836 | 29.355 |
| **Total** | **36.330** | **33.255** | **67.382** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 14 |
