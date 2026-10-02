# Evaluation Summary

Total cases: 111

## Composite Score
- average: 93.12

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 97.06
- quality: 89.19
- quality_passed: 0.89

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 4.473 | 1.804 | 19.190 |
| call_untrusted | 6.724 | 3.241 | 18.606 |
| reconstruct_response | 6.705 | 3.673 | 21.430 |
| **Total** | **17.902** | **9.981** | **48.091** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 15 |
