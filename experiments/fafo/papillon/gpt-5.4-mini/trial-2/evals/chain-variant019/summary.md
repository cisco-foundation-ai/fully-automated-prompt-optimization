# Evaluation Summary

Total cases: 111

## Composite Score
- average: 93.77

## Score Breakdown
- leakage_fraction: 0.05
- privacy: 94.74
- quality: 92.79
- quality_passed: 0.93

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 2.366 | 1.269 | 7.551 |
| call_untrusted | 3.510 | 2.156 | 10.035 |
| reconstruct_response | 2.503 | 1.492 | 7.341 |
| **Total** | **8.379** | **5.373** | **21.158** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 16 |
