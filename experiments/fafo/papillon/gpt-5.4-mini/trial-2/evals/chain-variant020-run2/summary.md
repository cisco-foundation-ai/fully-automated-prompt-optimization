# Evaluation Summary

Total cases: 111

## Composite Score
- average: 96.65

## Score Breakdown
- leakage_fraction: 0.04
- privacy: 96.01
- quality: 97.30
- quality_passed: 0.97

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 2.394 | 1.289 | 7.383 |
| call_untrusted | 3.794 | 2.033 | 14.603 |
| reconstruct_response | 3.010 | 1.675 | 9.902 |
| **Total** | **9.198** | **5.714** | **26.006** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 10 |
