# Evaluation Summary

Total cases: 111

## Composite Score
- average: 94.59

## Score Breakdown
- leakage_fraction: 0.06
- privacy: 93.67
- quality: 95.50
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 4.957 | 1.904 | 23.022 |
| call_untrusted | 6.780 | 3.354 | 20.232 |
| reconstruct_response | 7.512 | 4.597 | 24.039 |
| **Total** | **19.248** | **11.717** | **59.199** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 16 |
