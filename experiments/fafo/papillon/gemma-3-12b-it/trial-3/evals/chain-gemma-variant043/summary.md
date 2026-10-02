# Evaluation Summary

Total cases: 111

## Composite Score
- average: 95.92

## Score Breakdown
- leakage_fraction: 0.04
- privacy: 96.34
- quality: 95.50
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 4.719 | 1.501 | 24.070 |
| call_untrusted | 16.072 | 14.354 | 35.114 |
| reconstruct_response | 14.809 | 12.709 | 32.117 |
| **Total** | **35.600** | **33.577** | **84.551** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 13 |
