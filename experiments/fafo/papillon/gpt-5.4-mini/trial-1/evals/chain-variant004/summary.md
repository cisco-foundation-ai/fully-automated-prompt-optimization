# Evaluation Summary

Total cases: 111

## Composite Score
- average: 92.24

## Score Breakdown
- leakage_fraction: 0.10
- privacy: 89.88
- quality: 94.59
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 2.474 | 1.004 | 6.773 |
| call_untrusted | 3.309 | 2.038 | 11.757 |
| reconstruct_response | 2.412 | 1.633 | 6.976 |
| **Total** | **8.195** | **5.011** | **22.025** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 23 |
