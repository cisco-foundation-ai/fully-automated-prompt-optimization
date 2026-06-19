# Evaluation Summary

Total cases: 111

## Composite Score
- average: 94.40

## Score Breakdown
- leakage_fraction: 0.05
- privacy: 95.11
- quality: 93.69
- quality_passed: 0.94

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 5.714 | 1.549 | 22.419 |
| call_untrusted | 12.589 | 11.961 | 23.870 |
| reconstruct_response | 12.006 | 11.618 | 22.953 |
| **Total** | **30.309** | **26.384** | **59.261** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 14 |
