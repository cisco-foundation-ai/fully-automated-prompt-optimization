# Evaluation Summary

Total cases: 442

## Composite Score
- average: 96.19

## Score Breakdown
- leakage_fraction: 0.01
- privacy: 99.39
- quality: 92.99
- quality_passed: 0.93

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 2.169 | 1.188 | 6.628 |
| call_untrusted | 3.389 | 1.801 | 11.848 |
| reconstruct_response | 2.462 | 1.540 | 6.768 |
| **Total** | **8.021** | **5.235** | **22.452** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 40 |
