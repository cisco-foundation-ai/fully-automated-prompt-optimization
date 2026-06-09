# Evaluation Summary

Total cases: 111

## Composite Score
- average: 95.75

## Score Breakdown
- leakage_fraction: 0.04
- privacy: 96.01
- quality: 95.50
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.871 | 1.303 | 19.814 |
| call_untrusted | 12.037 | 11.349 | 22.834 |
| reconstruct_response | 12.489 | 11.066 | 25.341 |
| **Total** | **28.397** | **26.660** | **56.662** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 12 |
