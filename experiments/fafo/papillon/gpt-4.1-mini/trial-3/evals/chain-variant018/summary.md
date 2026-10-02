# Evaluation Summary

Total cases: 111

## Composite Score
- average: 95.87

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 97.15
- quality: 94.59
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 6.272 | 2.115 | 31.633 |
| call_untrusted | 7.199 | 3.391 | 26.779 |
| reconstruct_response | 8.947 | 5.050 | 30.086 |
| **Total** | **22.418** | **13.444** | **72.378** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 11 |
