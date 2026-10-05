# Evaluation Summary

Total cases: 111

## Composite Score
- average: 96.02

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 97.45
- quality: 94.59
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 4.717 | 1.845 | 23.205 |
| call_untrusted | 6.298 | 2.857 | 23.413 |
| reconstruct_response | 5.360 | 3.042 | 16.727 |
| **Total** | **16.375** | **8.773** | **46.510** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 9 |
