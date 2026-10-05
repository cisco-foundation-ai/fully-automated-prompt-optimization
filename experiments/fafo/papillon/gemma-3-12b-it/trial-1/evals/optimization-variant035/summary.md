# Evaluation Summary

Total cases: 111

## Composite Score
- average: 96.82

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 97.24
- quality: 96.40
- quality_passed: 0.96

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.464 | 1.171 | 16.700 |
| call_untrusted | 11.458 | 11.488 | 21.319 |
| reconstruct_response | 11.953 | 11.450 | 24.663 |
| **Total** | **26.875** | **24.283** | **51.429** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 10 |
