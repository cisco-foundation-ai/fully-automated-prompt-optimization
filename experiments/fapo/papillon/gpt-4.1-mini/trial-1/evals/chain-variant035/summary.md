# Evaluation Summary

Total cases: 111

## Composite Score
- average: 95.06

## Score Breakdown
- leakage_fraction: 0.04
- privacy: 95.53
- quality: 94.59
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 5.382 | 2.600 | 25.543 |
| call_untrusted | 7.982 | 4.116 | 23.433 |
| reconstruct_response | 7.191 | 3.919 | 24.838 |
| **Total** | **20.554** | **12.755** | **74.133** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 14 |
