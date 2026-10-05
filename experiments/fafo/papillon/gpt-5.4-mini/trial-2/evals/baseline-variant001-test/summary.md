# Evaluation Summary

Total cases: 221

## Composite Score
- average: 84.69

## Score Breakdown
- leakage_fraction: 0.23
- privacy: 77.06
- quality: 92.31
- quality_passed: 0.92

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.417 | 1.859 | 10.254 |
| call_untrusted | 4.567 | 2.302 | 16.202 |
| reconstruct_response | 3.382 | 2.062 | 12.310 |
| **Total** | **11.367** | **7.747** | **33.858** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 78 |
