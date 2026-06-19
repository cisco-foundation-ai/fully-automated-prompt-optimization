# Evaluation Summary

Total cases: 111

## Composite Score
- average: 97.18

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 97.06
- quality: 97.30
- quality_passed: 0.97

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.730 | 1.330 | 15.766 |
| call_untrusted | 11.832 | 11.122 | 25.684 |
| reconstruct_response | 11.885 | 11.691 | 24.966 |
| **Total** | **27.448** | **25.052** | **63.531** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 9 |
