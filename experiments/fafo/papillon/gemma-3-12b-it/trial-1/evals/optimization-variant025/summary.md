# Evaluation Summary

Total cases: 111

## Composite Score
- average: 95.17

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 96.64
- quality: 93.69
- quality_passed: 0.94

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.973 | 1.336 | 19.445 |
| call_untrusted | 12.525 | 11.840 | 24.411 |
| reconstruct_response | 12.535 | 11.931 | 24.132 |
| **Total** | **29.033** | **26.176** | **56.995** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 13 |
