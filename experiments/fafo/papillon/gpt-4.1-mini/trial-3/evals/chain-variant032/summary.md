# Evaluation Summary

Total cases: 111

## Composite Score
- average: 93.40

## Score Breakdown
- leakage_fraction: 0.04
- privacy: 95.81
- quality: 90.99
- quality_passed: 0.91

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 5.593 | 2.308 | 27.579 |
| call_untrusted | 9.689 | 4.711 | 35.398 |
| reconstruct_response | 9.802 | 6.869 | 30.106 |
| **Total** | **25.084** | **16.467** | **83.031** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 17 |
