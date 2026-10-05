# Evaluation Summary

Total cases: 111

## Composite Score
- average: 94.97

## Score Breakdown
- leakage_fraction: 0.04
- privacy: 96.25
- quality: 93.69
- quality_passed: 0.94

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 5.969 | 2.152 | 24.990 |
| call_untrusted | 8.525 | 4.513 | 26.983 |
| reconstruct_response | 10.740 | 6.345 | 32.148 |
| **Total** | **25.234** | **15.793** | **73.486** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 11 |
