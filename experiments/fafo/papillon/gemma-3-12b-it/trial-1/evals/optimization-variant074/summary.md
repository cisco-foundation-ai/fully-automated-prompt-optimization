# Evaluation Summary

Total cases: 111

## Composite Score
- average: 96.60

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 96.79
- quality: 96.40
- quality_passed: 0.96

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.708 | 1.262 | 18.989 |
| call_untrusted | 15.637 | 15.382 | 24.237 |
| reconstruct_response | 16.569 | 15.924 | 25.935 |
| **Total** | **35.913** | **35.210** | **58.079** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 10 |
