# Evaluation Summary

Total cases: 111

## Composite Score
- average: 95.53

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 97.36
- quality: 93.69
- quality_passed: 0.94

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.815 | 1.227 | 20.481 |
| call_untrusted | 16.095 | 16.526 | 23.717 |
| reconstruct_response | 17.356 | 17.435 | 27.600 |
| **Total** | **37.266** | **36.982** | **57.952** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 11 |
