# Evaluation Summary

Total cases: 111

## Composite Score
- average: 90.42

## Score Breakdown
- leakage_fraction: 0.08
- privacy: 91.66
- quality: 89.19
- quality_passed: 0.89

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 5.629 | 2.033 | 19.465 |
| call_untrusted | 5.847 | 2.871 | 19.248 |
| reconstruct_response | 5.849 | 3.474 | 15.642 |
| **Total** | **17.325** | **10.009** | **60.455** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 25 |
