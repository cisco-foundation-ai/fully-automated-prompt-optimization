# Evaluation Summary

Total cases: 111

## Composite Score
- average: 95.26

## Score Breakdown
- leakage_fraction: 0.06
- privacy: 94.13
- quality: 96.40
- quality_passed: 0.96

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 2.243 | 1.226 | 6.593 |
| call_untrusted | 3.249 | 1.754 | 13.657 |
| reconstruct_response | 2.433 | 1.362 | 9.166 |
| **Total** | **7.925** | **4.747** | **24.656** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 13 |
