# Evaluation Summary

Total cases: 111

## Composite Score
- average: 90.82

## Score Breakdown
- leakage_fraction: 0.07
- privacy: 93.36
- quality: 88.29
- quality_passed: 0.88

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 7.589 | 2.463 | 33.682 |
| call_untrusted | 7.602 | 4.788 | 21.801 |
| reconstruct_response | 7.558 | 4.673 | 22.515 |
| **Total** | **22.749** | **13.787** | **72.767** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 22 |
