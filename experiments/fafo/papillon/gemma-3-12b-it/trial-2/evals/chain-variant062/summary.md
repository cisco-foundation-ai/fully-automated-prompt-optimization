# Evaluation Summary

Total cases: 111

## Composite Score
- average: 96.07

## Score Breakdown
- leakage_fraction: 0.04
- privacy: 95.75
- quality: 96.40
- quality_passed: 0.96

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 4.071 | 1.371 | 18.435 |
| call_untrusted | 12.345 | 11.929 | 23.782 |
| reconstruct_response | 13.382 | 12.355 | 25.151 |
| **Total** | **29.798** | **26.242** | **59.118** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 11 |
