# Evaluation Summary

Total cases: 111

## Composite Score
- average: 94.40

## Score Breakdown
- leakage_fraction: 0.06
- privacy: 94.20
- quality: 94.59
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 4.150 | 1.266 | 20.279 |
| call_untrusted | 12.831 | 12.085 | 27.712 |
| reconstruct_response | 14.084 | 12.698 | 29.239 |
| **Total** | **31.064** | **27.883** | **57.187** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 15 |
