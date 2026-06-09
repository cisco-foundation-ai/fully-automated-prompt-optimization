# Evaluation Summary

Total cases: 111

## Composite Score
- average: 93.84

## Score Breakdown
- leakage_fraction: 0.06
- privacy: 93.99
- quality: 93.69
- quality_passed: 0.94

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 2.326 | 1.125 | 7.598 |
| call_untrusted | 3.873 | 2.018 | 13.737 |
| reconstruct_response | 2.846 | 1.727 | 8.024 |
| **Total** | **9.045** | **5.563** | **25.239** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 16 |
