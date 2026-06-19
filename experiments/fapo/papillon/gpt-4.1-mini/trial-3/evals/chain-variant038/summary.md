# Evaluation Summary

Total cases: 111

## Composite Score
- average: 94.97

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 97.15
- quality: 92.79
- quality_passed: 0.93

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 5.509 | 1.956 | 26.901 |
| call_untrusted | 7.864 | 3.937 | 26.352 |
| reconstruct_response | 8.882 | 4.978 | 25.689 |
| **Total** | **22.254** | **13.098** | **71.517** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 12 |
