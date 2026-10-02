# Evaluation Summary

Total cases: 111

## Composite Score
- average: 94.57

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 97.24
- quality: 91.89
- quality_passed: 0.92

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.713 | 1.290 | 17.564 |
| call_untrusted | 12.263 | 11.235 | 23.691 |
| reconstruct_response | 14.944 | 11.065 | 33.664 |
| **Total** | **30.920** | **26.124** | **59.296** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 14 |
