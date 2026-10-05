# Evaluation Summary

Total cases: 111

## Composite Score
- average: 94.83

## Score Breakdown
- leakage_fraction: 0.04
- privacy: 95.96
- quality: 93.69
- quality_passed: 0.94

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 5.573 | 1.651 | 33.997 |
| call_untrusted | 8.017 | 4.023 | 26.603 |
| reconstruct_response | 8.149 | 4.910 | 25.477 |
| **Total** | **21.738** | **11.046** | **72.133** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 14 |
