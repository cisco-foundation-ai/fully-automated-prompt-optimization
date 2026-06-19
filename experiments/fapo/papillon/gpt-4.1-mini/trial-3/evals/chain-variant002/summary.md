# Evaluation Summary

Total cases: 111

## Composite Score
- average: 89.64

## Score Breakdown
- leakage_fraction: 0.10
- privacy: 90.09
- quality: 89.19
- quality_passed: 0.89

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 5.876 | 1.895 | 39.879 |
| call_untrusted | 6.760 | 4.560 | 22.426 |
| reconstruct_response | 7.075 | 4.145 | 22.705 |
| **Total** | **19.710** | **11.080** | **69.715** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 27 |
