# Evaluation Summary

Total cases: 111

## Composite Score
- average: 93.89

## Score Breakdown
- leakage_fraction: 0.05
- privacy: 94.99
- quality: 92.79
- quality_passed: 0.93

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 4.143 | 1.534 | 21.079 |
| call_untrusted | 11.598 | 11.724 | 21.829 |
| reconstruct_response | 14.189 | 13.882 | 25.217 |
| **Total** | **29.930** | **27.606** | **56.525** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 16 |
