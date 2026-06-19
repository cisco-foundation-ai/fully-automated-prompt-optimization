# Evaluation Summary

Total cases: 111

## Composite Score
- average: 95.06

## Score Breakdown
- leakage_fraction: 0.04
- privacy: 95.53
- quality: 94.59
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 5.576 | 2.543 | 22.559 |
| call_untrusted | 8.437 | 4.738 | 29.888 |
| reconstruct_response | 9.680 | 5.599 | 34.110 |
| **Total** | **23.693** | **13.523** | **81.238** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 14 |
