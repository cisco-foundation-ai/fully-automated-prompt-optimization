# Evaluation Summary

Total cases: 111

## Composite Score
- average: 94.86

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 96.93
- quality: 92.79
- quality_passed: 0.93

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.481 | 1.207 | 17.514 |
| call_untrusted | 11.783 | 12.068 | 22.156 |
| reconstruct_response | 11.474 | 11.422 | 23.600 |
| **Total** | **26.738** | **26.161** | **49.369** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 14 |
