# Evaluation Summary

Total cases: 111

## Composite Score
- average: 95.60

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 96.61
- quality: 94.59
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 4.936 | 1.193 | 20.229 |
| call_untrusted | 11.431 | 11.755 | 20.476 |
| reconstruct_response | 11.168 | 10.993 | 21.972 |
| **Total** | **27.535** | **24.801** | **52.565** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 13 |
