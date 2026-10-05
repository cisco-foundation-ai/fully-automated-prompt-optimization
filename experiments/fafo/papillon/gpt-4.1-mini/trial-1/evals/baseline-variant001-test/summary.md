# Evaluation Summary

Total cases: 221

## Composite Score
- average: 67.20

## Score Breakdown
- leakage_fraction: 0.57
- privacy: 42.55
- quality: 91.86
- quality_passed: 0.92

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 6.073 | 3.701 | 18.682 |
| call_untrusted | 6.535 | 4.103 | 20.060 |
| reconstruct_response | 6.498 | 4.457 | 18.718 |
| **Total** | **19.106** | **13.729** | **53.523** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 153 |
