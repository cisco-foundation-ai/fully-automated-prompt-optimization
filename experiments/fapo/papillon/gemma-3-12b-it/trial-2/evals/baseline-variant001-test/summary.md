# Evaluation Summary

Total cases: 221

## Composite Score
- average: 65.83

## Score Breakdown
- leakage_fraction: 0.62
- privacy: 37.99
- quality: 93.67
- quality_passed: 0.94

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 10.979 | 4.570 | 18.796 |
| call_untrusted | 8.095 | 5.209 | 16.741 |
| reconstruct_response | 9.933 | 9.816 | 18.296 |
| **Total** | **29.007** | **19.888** | **48.943** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 158 |
