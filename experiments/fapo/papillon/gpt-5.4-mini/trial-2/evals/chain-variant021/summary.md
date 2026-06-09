# Evaluation Summary

Total cases: 111

## Composite Score
- average: 94.22

## Score Breakdown
- leakage_fraction: 0.06
- privacy: 93.84
- quality: 94.59
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 2.386 | 1.115 | 7.368 |
| call_untrusted | 4.053 | 2.041 | 16.042 |
| reconstruct_response | 2.850 | 1.603 | 9.519 |
| **Total** | **9.289** | **5.302** | **28.786** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 16 |
