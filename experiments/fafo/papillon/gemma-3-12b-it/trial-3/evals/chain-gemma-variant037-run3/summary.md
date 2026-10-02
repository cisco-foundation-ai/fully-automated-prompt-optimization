# Evaluation Summary

Total cases: 111

## Composite Score
- average: 94.71

## Score Breakdown
- leakage_fraction: 0.04
- privacy: 95.73
- quality: 93.69
- quality_passed: 0.94

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.568 | 1.256 | 18.654 |
| call_untrusted | 11.972 | 10.862 | 28.046 |
| reconstruct_response | 11.580 | 10.576 | 26.449 |
| **Total** | **27.121** | **24.226** | **60.651** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 15 |
