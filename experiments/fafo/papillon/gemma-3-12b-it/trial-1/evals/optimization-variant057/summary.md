# Evaluation Summary

Total cases: 111

## Composite Score
- average: 94.95

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 97.10
- quality: 92.79
- quality_passed: 0.93

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 5.245 | 1.882 | 24.272 |
| call_untrusted | 17.296 | 15.668 | 37.825 |
| reconstruct_response | 16.171 | 14.387 | 36.473 |
| **Total** | **38.712** | **35.394** | **80.348** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 14 |
