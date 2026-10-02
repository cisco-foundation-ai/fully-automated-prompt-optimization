# Evaluation Summary

Total cases: 111

## Composite Score
- average: 94.69

## Score Breakdown
- leakage_fraction: 0.05
- privacy: 94.79
- quality: 94.59
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.779 | 1.209 | 17.395 |
| call_untrusted | 11.941 | 10.930 | 26.054 |
| reconstruct_response | 12.379 | 11.936 | 22.531 |
| **Total** | **28.099** | **27.076** | **67.949** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 16 |
