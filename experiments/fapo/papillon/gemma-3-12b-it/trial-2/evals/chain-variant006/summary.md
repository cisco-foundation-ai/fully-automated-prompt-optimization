# Evaluation Summary

Total cases: 111

## Composite Score
- average: 94.17

## Score Breakdown
- leakage_fraction: 0.07
- privacy: 92.85
- quality: 95.50
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 4.121 | 1.493 | 18.935 |
| call_untrusted | 11.849 | 11.773 | 20.752 |
| reconstruct_response | 10.949 | 9.118 | 23.136 |
| **Total** | **26.919** | **24.469** | **52.799** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 15 |
