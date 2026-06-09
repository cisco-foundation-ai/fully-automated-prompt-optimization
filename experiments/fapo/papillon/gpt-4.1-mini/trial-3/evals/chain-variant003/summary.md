# Evaluation Summary

Total cases: 111

## Composite Score
- average: 92.22

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 97.06
- quality: 87.39
- quality_passed: 0.87

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.955 | 1.638 | 18.195 |
| call_untrusted | 7.505 | 2.711 | 29.385 |
| reconstruct_response | 6.177 | 3.233 | 18.727 |
| **Total** | **17.637** | **7.964** | **52.007** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 19 |
