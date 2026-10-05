# Evaluation Summary

Total cases: 111

## Composite Score
- average: 94.76

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 96.74
- quality: 92.79
- quality_passed: 0.93

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 5.171 | 1.592 | 23.493 |
| call_untrusted | 6.607 | 4.129 | 19.287 |
| reconstruct_response | 5.787 | 2.980 | 15.334 |
| **Total** | **17.564** | **10.339** | **52.144** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 15 |
