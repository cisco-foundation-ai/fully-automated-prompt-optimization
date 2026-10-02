# Evaluation Summary

Total cases: 111

## Composite Score
- average: 93.61

## Score Breakdown
- leakage_fraction: 0.06
- privacy: 93.53
- quality: 93.69
- quality_passed: 0.94

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 4.316 | 1.464 | 20.526 |
| call_untrusted | 11.541 | 11.310 | 20.460 |
| reconstruct_response | 8.678 | 8.328 | 22.726 |
| **Total** | **24.535** | **21.648** | **51.934** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 16 |
