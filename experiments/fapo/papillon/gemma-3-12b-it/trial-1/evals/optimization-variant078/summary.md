# Evaluation Summary

Total cases: 111

## Composite Score
- average: 94.70

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 96.61
- quality: 92.79
- quality_passed: 0.93

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.742 | 1.200 | 18.675 |
| call_untrusted | 10.909 | 9.665 | 24.429 |
| reconstruct_response | 12.016 | 10.969 | 27.385 |
| **Total** | **26.667** | **23.835** | **57.728** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 15 |
