# Evaluation Summary

Total cases: 111

## Composite Score
- average: 93.61

## Score Breakdown
- leakage_fraction: 0.06
- privacy: 93.52
- quality: 93.69
- quality_passed: 0.94

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 4.828 | 2.025 | 18.049 |
| call_untrusted | 6.118 | 2.886 | 22.477 |
| reconstruct_response | 6.828 | 3.048 | 25.831 |
| **Total** | **17.773** | **8.543** | **64.282** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 17 |
