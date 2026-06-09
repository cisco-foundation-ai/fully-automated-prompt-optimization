# Evaluation Summary

Total cases: 111

## Composite Score
- average: 92.38

## Score Breakdown
- leakage_fraction: 0.04
- privacy: 96.47
- quality: 88.29
- quality_passed: 0.88

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 5.834 | 1.954 | 25.343 |
| call_untrusted | 7.235 | 3.585 | 21.624 |
| reconstruct_response | 8.682 | 4.771 | 28.822 |
| **Total** | **21.751** | **13.647** | **73.744** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 19 |
