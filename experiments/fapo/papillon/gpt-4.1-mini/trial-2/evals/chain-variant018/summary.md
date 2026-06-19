# Evaluation Summary

Total cases: 111

## Composite Score
- average: 91.32

## Score Breakdown
- leakage_fraction: 0.08
- privacy: 91.65
- quality: 90.99
- quality_passed: 0.91

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 4.512 | 2.155 | 18.081 |
| call_untrusted | 6.919 | 3.793 | 18.224 |
| reconstruct_response | 4.544 | 2.393 | 17.303 |
| **Total** | **15.975** | **9.274** | **54.277** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 23 |
