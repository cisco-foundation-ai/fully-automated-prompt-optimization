# Evaluation Summary

Total cases: 111

## Composite Score
- average: 93.85

## Score Breakdown
- leakage_fraction: 0.06
- privacy: 94.00
- quality: 93.69
- quality_passed: 0.94

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 4.928 | 1.764 | 20.455 |
| call_untrusted | 11.947 | 10.910 | 26.822 |
| reconstruct_response | 14.849 | 10.973 | 22.708 |
| **Total** | **31.724** | **26.248** | **73.708** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 17 |
