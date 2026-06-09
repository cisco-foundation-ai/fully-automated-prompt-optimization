# Evaluation Summary

Total cases: 111

## Composite Score
- average: 92.64

## Score Breakdown
- leakage_fraction: 0.07
- privacy: 93.39
- quality: 91.89
- quality_passed: 0.92

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.102 | 1.282 | 11.265 |
| call_untrusted | 4.579 | 2.415 | 16.513 |
| reconstruct_response | 3.604 | 1.949 | 11.164 |
| **Total** | **11.285** | **6.646** | **37.177** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 19 |
