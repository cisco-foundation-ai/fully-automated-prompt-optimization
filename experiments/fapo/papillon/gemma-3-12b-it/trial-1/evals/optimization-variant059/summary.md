# Evaluation Summary

Total cases: 111

## Composite Score
- average: 95.09

## Score Breakdown
- leakage_fraction: 0.05
- privacy: 94.69
- quality: 95.50
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 5.593 | 2.102 | 23.941 |
| call_untrusted | 18.485 | 16.390 | 36.427 |
| reconstruct_response | 18.423 | 17.356 | 39.051 |
| **Total** | **42.501** | **41.476** | **86.222** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 15 |
