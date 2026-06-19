# Evaluation Summary

Total cases: 111

## Composite Score
- average: 91.61

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 96.73
- quality: 86.49
- quality_passed: 0.86

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 5.508 | 1.891 | 29.449 |
| call_untrusted | 6.787 | 3.712 | 20.007 |
| reconstruct_response | 6.755 | 4.256 | 18.780 |
| **Total** | **19.050** | **10.986** | **70.164** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 20 |
