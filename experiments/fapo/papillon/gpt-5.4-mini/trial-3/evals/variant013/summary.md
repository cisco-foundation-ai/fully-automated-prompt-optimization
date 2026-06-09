# Evaluation Summary

Total cases: 111

## Composite Score
- average: 95.95

## Score Breakdown
- leakage_fraction: 0.00
- privacy: 100.00
- quality: 91.89
- quality_passed: 0.92

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 1.598 | 1.095 | 4.169 |
| call_untrusted | 3.298 | 1.743 | 14.122 |
| reconstruct_response | 2.372 | 1.396 | 9.589 |
| **Total** | **7.269** | **4.577** | **24.170** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 9 |
