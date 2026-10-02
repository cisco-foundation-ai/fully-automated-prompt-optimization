# Evaluation Summary

Total cases: 111

## Composite Score
- average: 94.05

## Score Breakdown
- leakage_fraction: 0.06
- privacy: 94.41
- quality: 93.69
- quality_passed: 0.94

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.835 | 1.182 | 18.544 |
| call_untrusted | 11.701 | 11.032 | 24.208 |
| reconstruct_response | 12.410 | 11.412 | 23.455 |
| **Total** | **27.946** | **24.889** | **60.118** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 18 |
