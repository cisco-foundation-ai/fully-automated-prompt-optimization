# Evaluation Summary

Total cases: 111

## Composite Score
- average: 96.88

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 97.36
- quality: 96.40
- quality_passed: 0.96

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.508 | 1.168 | 18.914 |
| call_untrusted | 11.572 | 10.283 | 20.122 |
| reconstruct_response | 12.924 | 12.133 | 24.201 |
| **Total** | **28.003** | **24.840** | **57.554** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 9 |
