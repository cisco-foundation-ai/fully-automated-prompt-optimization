# Evaluation Summary

Total cases: 111

## Composite Score
- average: 94.06

## Score Breakdown
- leakage_fraction: 0.05
- privacy: 95.33
- quality: 92.79
- quality_passed: 0.93

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 5.137 | 2.279 | 28.517 |
| call_untrusted | 7.393 | 3.709 | 25.562 |
| reconstruct_response | 7.645 | 4.108 | 25.094 |
| **Total** | **20.175** | **11.124** | **73.253** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 17 |
