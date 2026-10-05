# Evaluation Summary

Total cases: 111

## Composite Score
- average: 93.95

## Score Breakdown
- leakage_fraction: 0.07
- privacy: 93.30
- quality: 94.59
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 2.130 | 1.254 | 7.701 |
| call_untrusted | 4.319 | 2.137 | 16.562 |
| reconstruct_response | 3.133 | 1.609 | 10.480 |
| **Total** | **9.582** | **5.598** | **31.051** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 18 |
