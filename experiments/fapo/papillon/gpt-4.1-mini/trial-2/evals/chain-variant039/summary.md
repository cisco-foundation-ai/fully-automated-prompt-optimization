# Evaluation Summary

Total cases: 111

## Composite Score
- average: 92.97

## Score Breakdown
- leakage_fraction: 0.04
- privacy: 95.85
- quality: 90.09
- quality_passed: 0.90

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 6.355 | 2.850 | 27.847 |
| call_untrusted | 8.204 | 3.622 | 28.165 |
| reconstruct_response | 9.030 | 4.344 | 27.980 |
| **Total** | **23.589** | **13.196** | **76.445** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 18 |
