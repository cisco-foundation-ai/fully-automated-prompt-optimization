# Evaluation Summary

Total cases: 111

## Composite Score
- average: 89.54

## Score Breakdown
- leakage_fraction: 0.12
- privacy: 88.10
- quality: 90.99
- quality_passed: 0.91

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 4.491 | 1.556 | 19.520 |
| call_untrusted | 12.035 | 11.605 | 23.879 |
| reconstruct_response | 10.993 | 10.613 | 23.893 |
| **Total** | **27.520** | **24.753** | **54.677** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 27 |
