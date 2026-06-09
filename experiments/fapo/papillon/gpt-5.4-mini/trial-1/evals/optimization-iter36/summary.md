# Evaluation Summary

Total cases: 111

## Composite Score
- average: 93.37

## Score Breakdown
- leakage_fraction: 0.07
- privacy: 93.06
- quality: 93.69
- quality_passed: 0.94

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 2.477 | 1.240 | 9.403 |
| call_untrusted | 4.532 | 2.194 | 16.570 |
| reconstruct_response | 3.339 | 1.641 | 9.858 |
| **Total** | **10.348** | **6.189** | **28.716** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 19 |
