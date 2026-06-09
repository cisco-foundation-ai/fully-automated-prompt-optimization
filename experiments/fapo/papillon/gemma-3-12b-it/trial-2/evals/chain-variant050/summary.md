# Evaluation Summary

Total cases: 111

## Composite Score
- average: 94.92

## Score Breakdown
- leakage_fraction: 0.06
- privacy: 94.34
- quality: 95.50
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.508 | 1.250 | 16.911 |
| call_untrusted | 12.100 | 10.827 | 25.845 |
| reconstruct_response | 12.418 | 11.952 | 25.054 |
| **Total** | **28.026** | **26.738** | **58.893** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 14 |
