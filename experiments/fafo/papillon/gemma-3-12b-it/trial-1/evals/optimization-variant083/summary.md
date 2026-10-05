# Evaluation Summary

Total cases: 111

## Composite Score
- average: 97.43

## Score Breakdown
- leakage_fraction: 0.02
- privacy: 97.57
- quality: 97.30
- quality_passed: 0.97

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.663 | 1.314 | 18.708 |
| call_untrusted | 15.391 | 15.833 | 25.062 |
| reconstruct_response | 16.763 | 16.836 | 29.005 |
| **Total** | **35.816** | **35.556** | **58.470** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 6 |
