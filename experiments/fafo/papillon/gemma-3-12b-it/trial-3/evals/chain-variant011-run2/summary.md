# Evaluation Summary

Total cases: 111

## Composite Score
- average: 97.17

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 97.03
- quality: 97.30
- quality_passed: 0.97

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 4.770 | 1.790 | 20.672 |
| call_untrusted | 6.021 | 3.377 | 19.080 |
| reconstruct_response | 5.898 | 2.750 | 19.164 |
| **Total** | **16.689** | **9.500** | **51.518** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 9 |
