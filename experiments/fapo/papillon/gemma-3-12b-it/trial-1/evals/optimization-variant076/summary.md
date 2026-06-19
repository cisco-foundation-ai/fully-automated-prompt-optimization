# Evaluation Summary

Total cases: 111

## Composite Score
- average: 97.21

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 97.13
- quality: 97.30
- quality_passed: 0.97

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.644 | 1.270 | 18.106 |
| call_untrusted | 17.235 | 16.319 | 31.282 |
| reconstruct_response | 17.281 | 16.694 | 29.798 |
| **Total** | **38.160** | **37.195** | **69.097** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 9 |
