# Evaluation Summary

Total cases: 111

## Composite Score
- average: 96.11

## Score Breakdown
- leakage_fraction: 0.06
- privacy: 94.02
- quality: 98.20
- quality_passed: 0.98

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 4.713 | 1.850 | 20.741 |
| call_untrusted | 6.554 | 3.073 | 23.040 |
| reconstruct_response | 6.605 | 3.500 | 19.392 |
| **Total** | **17.872** | **10.380** | **59.750** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 13 |
