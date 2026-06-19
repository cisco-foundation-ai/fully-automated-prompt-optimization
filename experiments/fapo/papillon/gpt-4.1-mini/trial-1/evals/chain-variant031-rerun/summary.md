# Evaluation Summary

Total cases: 111

## Composite Score
- average: 94.68

## Score Breakdown
- leakage_fraction: 0.04
- privacy: 95.66
- quality: 93.69
- quality_passed: 0.94

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 6.450 | 2.760 | 26.171 |
| call_untrusted | 7.160 | 4.056 | 28.913 |
| reconstruct_response | 7.133 | 3.636 | 21.026 |
| **Total** | **20.743** | **12.351** | **67.155** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 14 |
