# Evaluation Summary

Total cases: 111

## Composite Score
- average: 95.72

## Score Breakdown
- leakage_fraction: 0.00
- privacy: 99.55
- quality: 91.89
- quality_passed: 0.92

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 1.820 | 1.089 | 6.000 |
| call_untrusted | 3.509 | 1.950 | 11.013 |
| reconstruct_response | 2.283 | 1.386 | 7.544 |
| **Total** | **7.612** | **5.019** | **21.886** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 11 |
