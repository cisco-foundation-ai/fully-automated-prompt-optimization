# Evaluation Summary

Total cases: 111

## Composite Score
- average: 95.05

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 97.30
- quality: 92.79
- quality_passed: 0.93

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 4.339 | 1.515 | 21.178 |
| call_untrusted | 15.501 | 14.020 | 38.831 |
| reconstruct_response | 15.530 | 14.974 | 31.643 |
| **Total** | **35.371** | **32.197** | **72.067** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 12 |
