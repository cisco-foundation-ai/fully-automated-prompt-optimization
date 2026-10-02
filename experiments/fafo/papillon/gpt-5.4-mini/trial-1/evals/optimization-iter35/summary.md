# Evaluation Summary

Total cases: 111

## Composite Score
- average: 93.01

## Score Breakdown
- leakage_fraction: 0.07
- privacy: 93.22
- quality: 92.79
- quality_passed: 0.93

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 2.256 | 1.306 | 7.636 |
| call_untrusted | 4.181 | 2.284 | 17.036 |
| reconstruct_response | 2.873 | 1.874 | 9.474 |
| **Total** | **9.311** | **5.973** | **28.219** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 17 |
