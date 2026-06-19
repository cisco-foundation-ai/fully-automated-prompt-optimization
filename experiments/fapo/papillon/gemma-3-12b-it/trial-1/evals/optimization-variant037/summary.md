# Evaluation Summary

Total cases: 111

## Composite Score
- average: 96.64

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 96.89
- quality: 96.40
- quality_passed: 0.96

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 4.939 | 1.239 | 17.724 |
| call_untrusted | 11.424 | 11.018 | 21.644 |
| reconstruct_response | 12.026 | 11.542 | 23.236 |
| **Total** | **28.389** | **25.679** | **52.787** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 11 |
