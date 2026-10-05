# Evaluation Summary

Total cases: 111

## Composite Score
- average: 97.67

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 97.15
- quality: 98.20
- quality_passed: 0.98

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 6.297 | 1.797 | 30.049 |
| call_untrusted | 7.320 | 4.219 | 28.466 |
| reconstruct_response | 6.886 | 3.527 | 24.341 |
| **Total** | **20.503** | **10.458** | **75.538** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 7 |
