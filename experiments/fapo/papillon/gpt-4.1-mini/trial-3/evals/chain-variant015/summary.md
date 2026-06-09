# Evaluation Summary

Total cases: 111

## Composite Score
- average: 91.52

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 96.55
- quality: 86.49
- quality_passed: 0.86

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 4.738 | 1.906 | 21.214 |
| call_untrusted | 7.619 | 3.885 | 26.119 |
| reconstruct_response | 7.863 | 4.814 | 21.017 |
| **Total** | **20.220** | **11.741** | **59.240** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 19 |
