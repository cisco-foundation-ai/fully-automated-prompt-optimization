# Evaluation Summary

Total cases: 111

## Composite Score
- average: 93.51

## Score Breakdown
- leakage_fraction: 0.04
- privacy: 96.02
- quality: 90.99
- quality_passed: 0.91

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 6.941 | 1.994 | 25.505 |
| call_untrusted | 8.082 | 4.887 | 32.254 |
| reconstruct_response | 8.288 | 4.906 | 24.324 |
| **Total** | **23.311** | **14.546** | **82.528** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 16 |
