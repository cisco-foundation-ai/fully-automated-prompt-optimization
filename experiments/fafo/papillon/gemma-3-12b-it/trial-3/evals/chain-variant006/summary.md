# Evaluation Summary

Total cases: 111

## Composite Score
- average: 94.07

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 97.15
- quality: 90.99
- quality_passed: 0.91

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 5.024 | 1.708 | 20.932 |
| call_untrusted | 6.798 | 3.411 | 24.911 |
| reconstruct_response | 5.672 | 3.148 | 19.704 |
| **Total** | **17.494** | **8.541** | **63.963** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 15 |
