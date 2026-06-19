# Evaluation Summary

Total cases: 111

## Composite Score
- average: 92.61

## Score Breakdown
- leakage_fraction: 0.08
- privacy: 92.44
- quality: 92.79
- quality_passed: 0.93

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 6.745 | 2.199 | 31.721 |
| call_untrusted | 6.264 | 3.274 | 20.634 |
| reconstruct_response | 6.103 | 3.113 | 20.724 |
| **Total** | **19.113** | **11.326** | **64.181** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 18 |
