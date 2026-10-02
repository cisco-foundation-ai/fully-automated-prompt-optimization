# Evaluation Summary

Total cases: 111

## Composite Score
- average: 94.72

## Score Breakdown
- leakage_fraction: 0.05
- privacy: 94.85
- quality: 94.59
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.888 | 1.174 | 17.975 |
| call_untrusted | 10.850 | 10.722 | 20.539 |
| reconstruct_response | 11.675 | 11.134 | 23.126 |
| **Total** | **26.412** | **24.239** | **55.525** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 14 |
