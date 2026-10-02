# Evaluation Summary

Total cases: 111

## Composite Score
- average: 90.58

## Score Breakdown
- leakage_fraction: 0.09
- privacy: 91.07
- quality: 90.09
- quality_passed: 0.90

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.187 | 1.117 | 10.260 |
| call_untrusted | 3.946 | 2.132 | 16.307 |
| reconstruct_response | 2.694 | 1.497 | 10.220 |
| **Total** | **9.827** | **5.098** | **28.500** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 24 |
| redact_query | 1 |
