# Evaluation Summary

Total cases: 111

## Composite Score
- average: 96.53

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 96.67
- quality: 96.40
- quality_passed: 0.96

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.383 | 1.206 | 16.408 |
| call_untrusted | 10.965 | 11.272 | 20.686 |
| reconstruct_response | 10.350 | 10.455 | 19.583 |
| **Total** | **24.698** | **23.989** | **46.782** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 10 |
