# Evaluation Summary

Total cases: 111

## Composite Score
- average: 91.79

## Score Breakdown
- leakage_fraction: 0.07
- privacy: 92.59
- quality: 90.99
- quality_passed: 0.91

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 6.315 | 2.068 | 31.181 |
| call_untrusted | 7.250 | 3.427 | 24.199 |
| reconstruct_response | 6.647 | 3.910 | 28.662 |
| **Total** | **20.213** | **10.686** | **80.047** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 21 |
