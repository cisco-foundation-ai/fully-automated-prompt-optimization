# Evaluation Summary

Total cases: 111

## Composite Score
- average: 94.09

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 97.19
- quality: 90.99
- quality_passed: 0.91

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.666 | 1.200 | 19.630 |
| call_untrusted | 12.350 | 11.346 | 23.467 |
| reconstruct_response | 11.050 | 9.874 | 23.354 |
| **Total** | **27.066** | **24.290** | **56.403** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 16 |
