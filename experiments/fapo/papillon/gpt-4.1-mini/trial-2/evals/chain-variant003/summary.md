# Evaluation Summary

Total cases: 111

## Composite Score
- average: 92.69

## Score Breakdown
- leakage_fraction: 0.06
- privacy: 94.39
- quality: 90.99
- quality_passed: 0.91

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 6.128 | 2.058 | 26.808 |
| call_untrusted | 7.172 | 4.146 | 22.220 |
| reconstruct_response | 5.923 | 4.150 | 16.976 |
| **Total** | **19.222** | **12.335** | **65.118** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 17 |
