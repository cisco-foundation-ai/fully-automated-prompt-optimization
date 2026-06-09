# Evaluation Summary

Total cases: 111

## Composite Score
- average: 95.72

## Score Breakdown
- leakage_fraction: 0.04
- privacy: 95.95
- quality: 95.50
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 4.927 | 2.055 | 22.216 |
| call_untrusted | 8.982 | 4.831 | 25.230 |
| reconstruct_response | 8.693 | 5.268 | 20.850 |
| **Total** | **22.602** | **15.402** | **58.094** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 13 |
