# Evaluation Summary

Total cases: 111

## Composite Score
- average: 93.49

## Score Breakdown
- leakage_fraction: 0.06
- privacy: 94.19
- quality: 92.79
- quality_passed: 0.93

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.797 | 1.223 | 17.179 |
| call_untrusted | 11.295 | 10.123 | 21.559 |
| reconstruct_response | 12.553 | 11.426 | 23.477 |
| **Total** | **27.645** | **23.987** | **58.827** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 17 |
