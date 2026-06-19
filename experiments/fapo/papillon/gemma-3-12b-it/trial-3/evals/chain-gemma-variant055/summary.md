# Evaluation Summary

Total cases: 111

## Composite Score
- average: 94.56

## Score Breakdown
- leakage_fraction: 0.04
- privacy: 96.33
- quality: 92.79
- quality_passed: 0.93

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 5.450 | 1.422 | 20.661 |
| call_untrusted | 13.375 | 12.654 | 30.065 |
| reconstruct_response | 12.405 | 12.106 | 24.387 |
| **Total** | **31.230** | **28.145** | **69.316** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 15 |
