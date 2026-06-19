# Evaluation Summary

Total cases: 111

## Composite Score
- average: 93.94

## Score Breakdown
- leakage_fraction: 0.06
- privacy: 94.19
- quality: 93.69
- quality_passed: 0.94

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 4.117 | 1.274 | 20.001 |
| call_untrusted | 12.356 | 11.698 | 23.008 |
| reconstruct_response | 12.385 | 12.163 | 24.103 |
| **Total** | **28.858** | **25.755** | **57.366** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 17 |
