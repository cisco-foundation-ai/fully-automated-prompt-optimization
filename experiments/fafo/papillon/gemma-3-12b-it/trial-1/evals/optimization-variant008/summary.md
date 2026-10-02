# Evaluation Summary

Total cases: 111

## Composite Score
- average: 92.61

## Score Breakdown
- leakage_fraction: 0.05
- privacy: 95.14
- quality: 90.09
- quality_passed: 0.90

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.822 | 1.275 | 16.728 |
| call_untrusted | 12.131 | 11.912 | 26.706 |
| reconstruct_response | 11.472 | 10.444 | 24.351 |
| **Total** | **27.425** | **26.076** | **53.984** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 20 |
