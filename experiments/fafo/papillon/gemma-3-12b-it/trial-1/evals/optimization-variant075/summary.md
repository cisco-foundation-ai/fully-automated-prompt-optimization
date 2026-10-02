# Evaluation Summary

Total cases: 111

## Composite Score
- average: 95.38

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 97.06
- quality: 93.69
- quality_passed: 0.94

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 5.105 | 1.297 | 17.973 |
| call_untrusted | 15.867 | 15.049 | 25.664 |
| reconstruct_response | 16.094 | 15.730 | 26.753 |
| **Total** | **37.066** | **34.620** | **65.421** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 13 |
