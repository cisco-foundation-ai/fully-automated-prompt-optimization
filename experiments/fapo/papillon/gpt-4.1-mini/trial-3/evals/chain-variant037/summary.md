# Evaluation Summary

Total cases: 111

## Composite Score
- average: 93.98

## Score Breakdown
- leakage_fraction: 0.04
- privacy: 96.08
- quality: 91.89
- quality_passed: 0.92

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 5.515 | 1.822 | 26.624 |
| call_untrusted | 8.061 | 4.372 | 26.775 |
| reconstruct_response | 8.299 | 5.559 | 26.459 |
| **Total** | **21.875** | **13.496** | **77.859** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 16 |
