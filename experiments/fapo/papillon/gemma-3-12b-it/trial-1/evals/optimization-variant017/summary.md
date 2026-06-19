# Evaluation Summary

Total cases: 111

## Composite Score
- average: 97.09

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 96.89
- quality: 97.30
- quality_passed: 0.97

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.533 | 1.179 | 18.013 |
| call_untrusted | 12.485 | 11.705 | 26.381 |
| reconstruct_response | 12.095 | 11.782 | 23.589 |
| **Total** | **28.113** | **26.465** | **57.254** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 10 |
