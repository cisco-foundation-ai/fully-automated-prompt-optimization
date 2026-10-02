# Evaluation Summary

Total cases: 111

## Composite Score
- average: 95.74

## Score Breakdown
- leakage_fraction: 0.05
- privacy: 95.09
- quality: 96.40
- quality_passed: 0.96

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.681 | 1.255 | 17.395 |
| call_untrusted | 12.318 | 12.376 | 23.439 |
| reconstruct_response | 12.895 | 12.430 | 25.547 |
| **Total** | **28.893** | **26.638** | **57.233** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 14 |
