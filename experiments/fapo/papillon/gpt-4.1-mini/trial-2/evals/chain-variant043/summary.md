# Evaluation Summary

Total cases: 111

## Composite Score
- average: 95.79

## Score Breakdown
- leakage_fraction: 0.05
- privacy: 95.18
- quality: 96.40
- quality_passed: 0.96

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 7.664 | 2.265 | 25.513 |
| call_untrusted | 7.410 | 4.103 | 20.013 |
| reconstruct_response | 7.332 | 4.617 | 22.588 |
| **Total** | **22.406** | **13.109** | **66.089** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 12 |
