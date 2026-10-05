# Evaluation Summary

Total cases: 111

## Composite Score
- average: 91.68

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 96.87
- quality: 86.49
- quality_passed: 0.86

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 6.163 | 2.087 | 30.809 |
| call_untrusted | 8.456 | 4.347 | 32.829 |
| reconstruct_response | 8.823 | 4.864 | 31.131 |
| **Total** | **23.442** | **14.658** | **76.863** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 20 |
