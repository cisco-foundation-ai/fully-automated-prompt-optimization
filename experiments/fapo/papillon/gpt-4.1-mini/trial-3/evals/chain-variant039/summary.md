# Evaluation Summary

Total cases: 111

## Composite Score
- average: 94.41

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 96.92
- quality: 91.89
- quality_passed: 0.92

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 5.625 | 1.918 | 23.729 |
| call_untrusted | 7.167 | 4.390 | 23.431 |
| reconstruct_response | 7.986 | 5.357 | 22.493 |
| **Total** | **20.777** | **13.242** | **65.037** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 14 |
