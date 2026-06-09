# Evaluation Summary

Total cases: 111

## Composite Score
- average: 94.07

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 97.15
- quality: 90.99
- quality_passed: 0.91

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 4.503 | 1.610 | 16.781 |
| call_untrusted | 5.122 | 2.957 | 15.675 |
| reconstruct_response | 5.562 | 2.611 | 15.559 |
| **Total** | **15.187** | **8.647** | **59.075** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 13 |
