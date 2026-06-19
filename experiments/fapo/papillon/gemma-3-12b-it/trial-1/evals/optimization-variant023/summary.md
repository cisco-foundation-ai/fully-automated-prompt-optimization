# Evaluation Summary

Total cases: 111

## Composite Score
- average: 96.26

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 97.02
- quality: 95.50
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.585 | 1.206 | 17.582 |
| call_untrusted | 12.013 | 11.775 | 21.291 |
| reconstruct_response | 12.957 | 11.946 | 26.449 |
| **Total** | **28.555** | **26.665** | **57.459** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 11 |
