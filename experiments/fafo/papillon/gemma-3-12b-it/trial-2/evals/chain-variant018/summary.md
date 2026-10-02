# Evaluation Summary

Total cases: 111

## Composite Score
- average: 93.16

## Score Breakdown
- leakage_fraction: 0.04
- privacy: 96.23
- quality: 90.09
- quality_passed: 0.90

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.716 | 1.268 | 16.996 |
| call_untrusted | 11.501 | 11.170 | 20.481 |
| reconstruct_response | 9.479 | 8.489 | 21.414 |
| **Total** | **24.695** | **21.694** | **48.907** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 18 |
