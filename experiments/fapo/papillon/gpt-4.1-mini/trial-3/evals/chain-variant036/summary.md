# Evaluation Summary

Total cases: 111

## Composite Score
- average: 94.98

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 97.17
- quality: 92.79
- quality_passed: 0.93

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 5.602 | 1.987 | 24.704 |
| call_untrusted | 7.428 | 3.601 | 20.205 |
| reconstruct_response | 9.253 | 5.150 | 30.261 |
| **Total** | **22.283** | **12.984** | **67.553** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 12 |
