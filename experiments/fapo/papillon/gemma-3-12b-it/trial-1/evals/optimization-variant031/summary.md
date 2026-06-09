# Evaluation Summary

Total cases: 111

## Composite Score
- average: 93.80

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 96.61
- quality: 90.99
- quality_passed: 0.91

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.412 | 1.172 | 18.068 |
| call_untrusted | 11.243 | 11.148 | 21.038 |
| reconstruct_response | 10.569 | 10.065 | 20.115 |
| **Total** | **25.225** | **23.440** | **51.038** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 15 |
