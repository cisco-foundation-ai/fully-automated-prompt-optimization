# Evaluation Summary

Total cases: 111

## Composite Score
- average: 85.74

## Score Breakdown
- leakage_fraction: 0.21
- privacy: 78.69
- quality: 92.79
- quality_passed: 0.93

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 6.422 | 2.314 | 24.060 |
| call_untrusted | 7.166 | 3.327 | 20.823 |
| reconstruct_response | 10.237 | 6.360 | 30.282 |
| **Total** | **23.824** | **13.490** | **82.768** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 36 |
