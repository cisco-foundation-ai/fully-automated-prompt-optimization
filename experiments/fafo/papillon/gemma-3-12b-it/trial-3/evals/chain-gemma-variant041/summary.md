# Evaluation Summary

Total cases: 111

## Composite Score
- average: 95.54

## Score Breakdown
- leakage_fraction: 0.04
- privacy: 95.59
- quality: 95.50
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.751 | 1.351 | 19.872 |
| call_untrusted | 12.847 | 11.598 | 23.348 |
| reconstruct_response | 11.725 | 11.444 | 23.279 |
| **Total** | **28.323** | **26.367** | **57.214** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 15 |
