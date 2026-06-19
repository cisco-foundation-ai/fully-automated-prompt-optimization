# Evaluation Summary

Total cases: 111

## Composite Score
- average: 96.80

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 97.20
- quality: 96.40
- quality_passed: 0.96

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.653 | 1.279 | 18.965 |
| call_untrusted | 11.712 | 11.642 | 23.322 |
| reconstruct_response | 11.743 | 11.594 | 24.433 |
| **Total** | **27.109** | **26.210** | **52.875** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 10 |
