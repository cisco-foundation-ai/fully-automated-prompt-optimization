# Evaluation Summary

Total cases: 111

## Composite Score
- average: 95.33

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 96.97
- quality: 93.69
- quality_passed: 0.94

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.832 | 1.244 | 19.073 |
| call_untrusted | 12.671 | 12.079 | 26.004 |
| reconstruct_response | 11.867 | 11.493 | 26.140 |
| **Total** | **28.370** | **26.585** | **59.438** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 13 |
