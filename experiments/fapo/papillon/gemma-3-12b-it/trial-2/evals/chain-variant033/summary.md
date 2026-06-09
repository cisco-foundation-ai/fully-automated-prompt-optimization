# Evaluation Summary

Total cases: 111

## Composite Score
- average: 96.61

## Score Breakdown
- leakage_fraction: 0.06
- privacy: 94.11
- quality: 99.10
- quality_passed: 0.99

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 5.110 | 1.293 | 17.356 |
| call_untrusted | 12.677 | 11.420 | 25.421 |
| reconstruct_response | 13.377 | 11.655 | 28.175 |
| **Total** | **31.164** | **26.290** | **58.021** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 9 |
