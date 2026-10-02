# Evaluation Summary

Total cases: 111

## Composite Score
- average: 95.59

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 96.59
- quality: 94.59
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.907 | 1.230 | 18.536 |
| call_untrusted | 12.923 | 12.334 | 24.139 |
| reconstruct_response | 12.107 | 11.604 | 23.527 |
| **Total** | **28.938** | **27.987** | **55.389** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 13 |
