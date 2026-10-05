# Evaluation Summary

Total cases: 111

## Composite Score
- average: 94.61

## Score Breakdown
- leakage_fraction: 0.06
- privacy: 93.73
- quality: 95.50
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.976 | 1.171 | 18.304 |
| call_untrusted | 12.427 | 11.877 | 22.463 |
| reconstruct_response | 12.792 | 12.078 | 23.397 |
| **Total** | **29.196** | **27.853** | **58.329** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 17 |
