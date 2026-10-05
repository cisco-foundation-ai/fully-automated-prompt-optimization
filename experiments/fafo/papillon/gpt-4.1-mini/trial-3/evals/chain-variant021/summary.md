# Evaluation Summary

Total cases: 111

## Composite Score
- average: 91.37

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 97.15
- quality: 85.59
- quality_passed: 0.86

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 6.048 | 1.990 | 26.666 |
| call_untrusted | 7.913 | 4.057 | 26.880 |
| reconstruct_response | 8.597 | 4.523 | 28.944 |
| **Total** | **22.557** | **14.500** | **67.883** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 18 |
