# Evaluation Summary

Total cases: 111

## Composite Score
- average: 95.13

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 96.56
- quality: 93.69
- quality_passed: 0.94

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.823 | 1.252 | 20.369 |
| call_untrusted | 12.228 | 11.710 | 24.963 |
| reconstruct_response | 12.010 | 11.215 | 27.556 |
| **Total** | **28.061** | **27.103** | **59.170** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 14 |
