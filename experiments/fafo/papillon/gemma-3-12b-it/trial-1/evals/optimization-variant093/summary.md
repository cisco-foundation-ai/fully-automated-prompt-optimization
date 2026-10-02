# Evaluation Summary

Total cases: 111

## Composite Score
- average: 97.14

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 96.99
- quality: 97.30
- quality_passed: 0.97

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.828 | 1.192 | 17.125 |
| call_untrusted | 14.772 | 14.300 | 25.090 |
| reconstruct_response | 15.777 | 14.641 | 28.190 |
| **Total** | **34.377** | **31.580** | **56.992** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 8 |
