# Evaluation Summary

Total cases: 111

## Composite Score
- average: 94.88

## Score Breakdown
- leakage_fraction: 0.04
- privacy: 96.06
- quality: 93.69
- quality_passed: 0.94

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 6.690 | 2.804 | 26.056 |
| call_untrusted | 9.645 | 5.323 | 29.971 |
| reconstruct_response | 8.114 | 5.693 | 26.068 |
| **Total** | **24.450** | **14.632** | **77.092** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 14 |
