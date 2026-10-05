# Evaluation Summary

Total cases: 111

## Composite Score
- average: 95.17

## Score Breakdown
- leakage_fraction: 0.04
- privacy: 95.75
- quality: 94.59
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 6.157 | 2.819 | 28.290 |
| call_untrusted | 7.667 | 4.288 | 28.413 |
| reconstruct_response | 8.396 | 4.670 | 24.648 |
| **Total** | **22.221** | **12.612** | **73.075** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 14 |
