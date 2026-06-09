# Evaluation Summary

Total cases: 221

## Composite Score
- average: 68.73

## Score Breakdown
- leakage_fraction: 0.55
- privacy: 45.15
- quality: 92.31
- quality_passed: 0.92

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 5.947 | 3.420 | 18.953 |
| call_untrusted | 6.801 | 3.713 | 26.642 |
| reconstruct_response | 7.282 | 4.176 | 23.795 |
| **Total** | **20.030** | **13.735** | **56.088** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 147 |
