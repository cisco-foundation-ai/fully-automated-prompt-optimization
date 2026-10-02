# Evaluation Summary

Total cases: 111

## Composite Score
- average: 95.89

## Score Breakdown
- leakage_fraction: 0.06
- privacy: 93.58
- quality: 98.20
- quality_passed: 0.98

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.589 | 1.210 | 17.231 |
| call_untrusted | 11.175 | 10.759 | 24.550 |
| reconstruct_response | 12.373 | 12.130 | 24.512 |
| **Total** | **27.137** | **25.717** | **51.115** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 12 |
