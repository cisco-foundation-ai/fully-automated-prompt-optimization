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
| redact_query | 4.764 | 1.507 | 20.228 |
| call_untrusted | 12.345 | 12.308 | 24.233 |
| reconstruct_response | 10.699 | 9.574 | 22.757 |
| **Total** | **27.807** | **25.393** | **58.972** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 18 |
