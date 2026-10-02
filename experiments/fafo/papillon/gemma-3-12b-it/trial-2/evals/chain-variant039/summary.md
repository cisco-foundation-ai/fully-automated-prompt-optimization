# Evaluation Summary

Total cases: 111

## Composite Score
- average: 96.04

## Score Breakdown
- leakage_fraction: 0.05
- privacy: 94.79
- quality: 97.30
- quality_passed: 0.97

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 4.907 | 1.067 | 17.217 |
| call_untrusted | 11.464 | 10.956 | 23.771 |
| reconstruct_response | 12.957 | 12.660 | 25.416 |
| **Total** | **29.329** | **26.191** | **57.685** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 13 |
