# Evaluation Summary

Total cases: 111

## Composite Score
- average: 95.00

## Score Breakdown
- leakage_fraction: 0.04
- privacy: 96.31
- quality: 93.69
- quality_passed: 0.94

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.751 | 1.290 | 19.140 |
| call_untrusted | 11.545 | 11.225 | 21.864 |
| reconstruct_response | 11.047 | 10.503 | 22.034 |
| **Total** | **26.342** | **24.602** | **50.803** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 14 |
