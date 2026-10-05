# Evaluation Summary

Total cases: 111

## Composite Score
- average: 94.47

## Score Breakdown
- leakage_fraction: 0.06
- privacy: 94.34
- quality: 94.59
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.927 | 1.172 | 19.804 |
| call_untrusted | 12.147 | 11.782 | 23.495 |
| reconstruct_response | 12.401 | 12.022 | 24.742 |
| **Total** | **28.476** | **26.932** | **61.388** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 15 |
