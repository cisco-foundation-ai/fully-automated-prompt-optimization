# Evaluation Summary

Total cases: 111

## Composite Score
- average: 94.77

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 96.74
- quality: 92.79
- quality_passed: 0.93

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 8.676 | 1.562 | 21.185 |
| call_untrusted | 11.778 | 11.280 | 23.585 |
| reconstruct_response | 11.309 | 11.233 | 21.780 |
| **Total** | **31.762** | **26.082** | **68.426** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 14 |
