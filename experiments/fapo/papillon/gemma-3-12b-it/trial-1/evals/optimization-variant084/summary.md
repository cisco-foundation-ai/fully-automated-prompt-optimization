# Evaluation Summary

Total cases: 111

## Composite Score
- average: 97.21

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 97.13
- quality: 97.30
- quality_passed: 0.97

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.787 | 1.250 | 19.277 |
| call_untrusted | 15.562 | 15.667 | 29.028 |
| reconstruct_response | 16.690 | 16.296 | 28.328 |
| **Total** | **36.039** | **35.374** | **59.447** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 9 |
