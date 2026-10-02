# Evaluation Summary

Total cases: 111

## Composite Score
- average: 93.62

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 97.15
- quality: 90.09
- quality_passed: 0.90

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 4.242 | 1.805 | 19.421 |
| call_untrusted | 5.536 | 2.492 | 21.991 |
| reconstruct_response | 5.776 | 2.575 | 18.677 |
| **Total** | **15.555** | **7.634** | **55.798** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 14 |
