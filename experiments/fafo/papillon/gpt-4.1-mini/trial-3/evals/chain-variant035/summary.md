# Evaluation Summary

Total cases: 111

## Composite Score
- average: 94.07

## Score Breakdown
- leakage_fraction: 0.04
- privacy: 96.25
- quality: 91.89
- quality_passed: 0.92

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 5.136 | 1.743 | 23.474 |
| call_untrusted | 7.008 | 3.669 | 22.520 |
| reconstruct_response | 9.324 | 4.550 | 34.197 |
| **Total** | **21.469** | **12.275** | **82.584** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 14 |
