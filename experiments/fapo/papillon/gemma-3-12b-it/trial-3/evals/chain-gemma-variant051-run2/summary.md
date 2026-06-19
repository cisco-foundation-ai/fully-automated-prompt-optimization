# Evaluation Summary

Total cases: 111

## Composite Score
- average: 94.35

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 96.82
- quality: 91.89
- quality_passed: 0.92

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.713 | 1.234 | 16.382 |
| call_untrusted | 12.735 | 12.292 | 24.348 |
| reconstruct_response | 11.728 | 11.270 | 26.409 |
| **Total** | **28.176** | **26.421** | **57.450** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 15 |
