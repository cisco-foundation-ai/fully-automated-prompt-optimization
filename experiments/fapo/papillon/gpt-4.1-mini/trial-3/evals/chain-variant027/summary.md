# Evaluation Summary

Total cases: 111

## Composite Score
- average: 92.64

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 97.00
- quality: 88.29
- quality_passed: 0.88

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 6.826 | 2.286 | 43.949 |
| call_untrusted | 10.452 | 5.551 | 40.307 |
| reconstruct_response | 9.142 | 5.678 | 27.532 |
| **Total** | **26.420** | **15.058** | **86.577** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 18 |
