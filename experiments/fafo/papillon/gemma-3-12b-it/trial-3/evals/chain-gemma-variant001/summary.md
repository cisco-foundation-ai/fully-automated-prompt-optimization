# Evaluation Summary

Total cases: 111

## Composite Score
- average: 94.47

## Score Breakdown
- leakage_fraction: 0.04
- privacy: 96.16
- quality: 92.79
- quality_passed: 0.93

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 6.374 | 1.742 | 22.893 |
| call_untrusted | 12.496 | 12.309 | 25.592 |
| reconstruct_response | 11.428 | 10.756 | 22.295 |
| **Total** | **30.298** | **26.101** | **63.960** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 15 |
