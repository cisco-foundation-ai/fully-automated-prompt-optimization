# Evaluation Summary

Total cases: 221

## Composite Score
- average: 94.03

## Score Breakdown
- leakage_fraction: 0.04
- privacy: 95.75
- quality: 92.31
- quality_passed: 0.92

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 2.843 | 1.386 | 9.860 |
| call_untrusted | 4.260 | 2.312 | 14.152 |
| reconstruct_response | 5.569 | 3.253 | 18.545 |
| **Total** | **12.672** | **7.926** | **42.362** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 32 |
