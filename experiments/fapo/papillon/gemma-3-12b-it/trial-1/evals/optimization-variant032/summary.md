# Evaluation Summary

Total cases: 111

## Composite Score
- average: 93.79

## Score Breakdown
- leakage_fraction: 0.04
- privacy: 95.69
- quality: 91.89
- quality_passed: 0.92

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.417 | 1.100 | 17.507 |
| call_untrusted | 10.990 | 10.663 | 22.787 |
| reconstruct_response | 10.666 | 10.431 | 23.208 |
| **Total** | **25.073** | **22.879** | **52.786** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 17 |
