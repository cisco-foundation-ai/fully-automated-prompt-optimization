# Evaluation Summary

Total cases: 111

## Composite Score
- average: 95.16

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 96.62
- quality: 93.69
- quality_passed: 0.94

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 5.873 | 1.981 | 27.805 |
| call_untrusted | 7.060 | 4.181 | 21.748 |
| reconstruct_response | 8.735 | 4.589 | 32.732 |
| **Total** | **21.668** | **13.244** | **68.233** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 14 |
