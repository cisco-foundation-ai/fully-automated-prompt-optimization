# Evaluation Summary

Total cases: 111

## Composite Score
- average: 96.13

## Score Breakdown
- leakage_fraction: 0.04
- privacy: 95.86
- quality: 96.40
- quality_passed: 0.96

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 4.062 | 1.332 | 20.109 |
| call_untrusted | 12.096 | 11.502 | 26.405 |
| reconstruct_response | 12.862 | 11.812 | 29.179 |
| **Total** | **29.020** | **24.796** | **61.189** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 12 |
