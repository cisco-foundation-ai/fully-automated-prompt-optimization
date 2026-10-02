# Evaluation Summary

Total cases: 111

## Composite Score
- average: 95.60

## Score Breakdown
- leakage_fraction: 0.05
- privacy: 94.80
- quality: 96.40
- quality_passed: 0.96

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.905 | 1.140 | 24.485 |
| call_untrusted | 11.902 | 11.007 | 22.588 |
| reconstruct_response | 12.229 | 11.528 | 23.863 |
| **Total** | **28.036** | **25.086** | **57.106** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 13 |
