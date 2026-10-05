# Evaluation Summary

Total cases: 111

## Composite Score
- average: 94.96

## Score Breakdown
- leakage_fraction: 0.05
- privacy: 95.33
- quality: 94.59
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 4.008 | 1.481 | 17.393 |
| call_untrusted | 11.537 | 11.255 | 20.892 |
| reconstruct_response | 12.640 | 13.039 | 23.550 |
| **Total** | **28.185** | **27.214** | **53.355** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 13 |
