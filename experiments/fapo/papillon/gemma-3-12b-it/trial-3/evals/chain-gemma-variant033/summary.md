# Evaluation Summary

Total cases: 111

## Composite Score
- average: 95.46

## Score Breakdown
- leakage_fraction: 0.04
- privacy: 96.33
- quality: 94.59
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.354 | 1.352 | 16.138 |
| call_untrusted | 11.426 | 11.721 | 22.496 |
| reconstruct_response | 11.561 | 11.240 | 24.887 |
| **Total** | **26.341** | **25.355** | **51.675** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 13 |
