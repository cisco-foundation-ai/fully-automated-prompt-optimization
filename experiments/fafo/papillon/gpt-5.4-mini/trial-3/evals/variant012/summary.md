# Evaluation Summary

Total cases: 111

## Composite Score
- average: 96.01

## Score Breakdown
- leakage_fraction: 0.01
- privacy: 99.23
- quality: 92.79
- quality_passed: 0.93

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 1.893 | 1.087 | 7.105 |
| call_untrusted | 3.294 | 1.795 | 10.059 |
| reconstruct_response | 2.509 | 1.447 | 6.609 |
| **Total** | **7.696** | **4.828** | **23.278** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 11 |
