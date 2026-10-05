# Evaluation Summary

Total cases: 111

## Composite Score
- average: 97.21

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 97.13
- quality: 97.30
- quality_passed: 0.97

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.627 | 1.283 | 18.023 |
| call_untrusted | 14.636 | 14.375 | 25.312 |
| reconstruct_response | 15.025 | 15.356 | 26.174 |
| **Total** | **33.287** | **33.237** | **57.900** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 9 |
