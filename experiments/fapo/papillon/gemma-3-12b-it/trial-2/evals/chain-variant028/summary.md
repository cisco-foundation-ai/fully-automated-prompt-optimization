# Evaluation Summary

Total cases: 111

## Composite Score
- average: 94.12

## Score Breakdown
- leakage_fraction: 0.06
- privacy: 93.64
- quality: 94.59
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.861 | 1.339 | 18.100 |
| call_untrusted | 12.415 | 12.113 | 28.409 |
| reconstruct_response | 11.591 | 10.177 | 25.657 |
| **Total** | **27.868** | **26.026** | **62.354** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 16 |
