# Evaluation Summary

Total cases: 111

## Composite Score
- average: 93.80

## Score Breakdown
- leakage_fraction: 0.08
- privacy: 92.11
- quality: 95.50
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 5.580 | 1.443 | 19.288 |
| call_untrusted | 13.533 | 12.431 | 25.527 |
| reconstruct_response | 11.921 | 11.440 | 23.109 |
| **Total** | **31.034** | **27.408** | **59.853** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 16 |
