# Evaluation Summary

Total cases: 111

## Composite Score
- average: 95.73

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 96.87
- quality: 94.59
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 6.033 | 2.828 | 28.645 |
| call_untrusted | 7.158 | 3.993 | 20.288 |
| reconstruct_response | 6.924 | 4.249 | 20.182 |
| **Total** | **20.115** | **12.949** | **73.022** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 11 |
