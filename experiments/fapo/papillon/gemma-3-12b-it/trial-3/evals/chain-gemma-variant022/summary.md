# Evaluation Summary

Total cases: 111

## Composite Score
- average: 95.19

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 96.69
- quality: 93.69
- quality_passed: 0.94

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.528 | 1.352 | 17.669 |
| call_untrusted | 12.464 | 11.454 | 26.803 |
| reconstruct_response | 11.085 | 10.140 | 22.822 |
| **Total** | **27.077** | **25.995** | **57.274** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 14 |
