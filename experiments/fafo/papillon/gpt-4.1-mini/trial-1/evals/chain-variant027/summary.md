# Evaluation Summary

Total cases: 111

## Composite Score
- average: 94.83

## Score Breakdown
- leakage_fraction: 0.04
- privacy: 95.96
- quality: 93.69
- quality_passed: 0.94

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 7.817 | 2.882 | 34.713 |
| call_untrusted | 9.687 | 4.655 | 29.834 |
| reconstruct_response | 9.673 | 5.211 | 34.956 |
| **Total** | **27.177** | **14.845** | **97.311** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 13 |
