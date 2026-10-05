# Evaluation Summary

Total cases: 111

## Composite Score
- average: 94.77

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 96.75
- quality: 92.79
- quality_passed: 0.93

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.814 | 1.381 | 17.542 |
| call_untrusted | 12.031 | 11.738 | 26.419 |
| reconstruct_response | 11.052 | 10.520 | 22.412 |
| **Total** | **26.897** | **25.547** | **53.456** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 15 |
