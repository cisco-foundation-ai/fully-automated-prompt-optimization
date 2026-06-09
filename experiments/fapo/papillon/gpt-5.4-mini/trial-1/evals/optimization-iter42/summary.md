# Evaluation Summary

Total cases: 111

## Composite Score
- average: 94.81

## Score Breakdown
- leakage_fraction: 0.06
- privacy: 94.13
- quality: 95.50
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 2.907 | 1.214 | 7.533 |
| call_untrusted | 4.555 | 2.317 | 17.552 |
| reconstruct_response | 3.267 | 1.787 | 11.812 |
| **Total** | **10.729** | **6.189** | **35.899** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 18 |
