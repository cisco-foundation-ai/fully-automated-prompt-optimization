# Evaluation Summary

Total cases: 111

## Composite Score
- average: 93.57

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 97.06
- quality: 90.09
- quality_passed: 0.90

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 4.332 | 1.590 | 19.131 |
| call_untrusted | 7.686 | 3.644 | 26.408 |
| reconstruct_response | 7.973 | 4.650 | 24.030 |
| **Total** | **19.991** | **11.134** | **53.734** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 17 |
