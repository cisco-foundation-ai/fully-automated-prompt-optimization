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
| redact_query | 3.968 | 1.288 | 17.856 |
| call_untrusted | 12.254 | 11.926 | 27.172 |
| reconstruct_response | 12.871 | 11.968 | 24.773 |
| **Total** | **29.093** | **26.920** | **60.325** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 15 |
