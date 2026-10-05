# Evaluation Summary

Total cases: 111

## Composite Score
- average: 89.75

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 96.62
- quality: 82.88
- quality_passed: 0.83

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 6.020 | 2.265 | 33.128 |
| call_untrusted | 6.404 | 3.655 | 21.186 |
| reconstruct_response | 6.199 | 3.735 | 17.967 |
| **Total** | **18.622** | **10.873** | **54.461** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 25 |
