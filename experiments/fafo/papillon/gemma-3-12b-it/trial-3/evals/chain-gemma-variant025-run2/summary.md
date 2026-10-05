# Evaluation Summary

Total cases: 111

## Composite Score
- average: 96.38

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 97.27
- quality: 95.50
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.991 | 1.320 | 18.619 |
| call_untrusted | 12.318 | 12.169 | 23.980 |
| reconstruct_response | 12.478 | 11.694 | 27.227 |
| **Total** | **28.788** | **26.791** | **55.716** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 10 |
