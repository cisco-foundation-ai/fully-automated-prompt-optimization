# Evaluation Summary

Total cases: 111

## Composite Score
- average: 95.18

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 96.67
- quality: 93.69
- quality_passed: 0.94

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.297 | 1.146 | 15.826 |
| call_untrusted | 11.701 | 11.405 | 21.375 |
| reconstruct_response | 11.170 | 10.872 | 23.336 |
| **Total** | **26.168** | **25.903** | **48.726** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 13 |
