# Evaluation Summary

Total cases: 111

## Composite Score
- average: 94.52

## Score Breakdown
- leakage_fraction: 0.04
- privacy: 96.25
- quality: 92.79
- quality_passed: 0.93

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 4.953 | 1.841 | 23.229 |
| call_untrusted | 8.458 | 4.378 | 27.459 |
| reconstruct_response | 9.113 | 5.710 | 28.093 |
| **Total** | **22.524** | **14.040** | **78.153** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 14 |
