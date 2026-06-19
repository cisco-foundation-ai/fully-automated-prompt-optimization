# Evaluation Summary

Total cases: 111

## Composite Score
- average: 92.15

## Score Breakdown
- leakage_fraction: 0.07
- privacy: 93.30
- quality: 90.99
- quality_passed: 0.91

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 7.350 | 2.696 | 35.382 |
| call_untrusted | 7.220 | 3.310 | 25.268 |
| reconstruct_response | 7.270 | 4.049 | 22.580 |
| **Total** | **21.840** | **12.160** | **92.142** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 21 |
