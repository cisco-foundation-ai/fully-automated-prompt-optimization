# Evaluation Summary

Total cases: 111

## Composite Score
- average: 94.89

## Score Breakdown
- leakage_fraction: 0.04
- privacy: 96.10
- quality: 93.69
- quality_passed: 0.94

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 2.459 | 1.355 | 8.737 |
| call_untrusted | 4.980 | 2.557 | 19.099 |
| reconstruct_response | 3.460 | 1.727 | 11.903 |
| **Total** | **10.899** | **6.864** | **33.118** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 15 |
