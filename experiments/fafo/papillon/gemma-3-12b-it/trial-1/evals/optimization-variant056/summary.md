# Evaluation Summary

Total cases: 111

## Composite Score
- average: 94.78

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 96.78
- quality: 92.79
- quality_passed: 0.93

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.632 | 1.297 | 17.837 |
| call_untrusted | 12.011 | 10.880 | 23.070 |
| reconstruct_response | 12.765 | 11.300 | 26.356 |
| **Total** | **28.408** | **26.013** | **58.220** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 15 |
