# Evaluation Summary

Total cases: 111

## Composite Score
- average: 91.07

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 97.45
- quality: 84.68
- quality_passed: 0.85

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 4.415 | 1.524 | 22.519 |
| call_untrusted | 7.168 | 3.456 | 21.806 |
| reconstruct_response | 7.105 | 3.743 | 21.049 |
| **Total** | **18.689** | **9.278** | **59.528** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 20 |
