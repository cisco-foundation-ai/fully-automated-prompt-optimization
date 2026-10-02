# Evaluation Summary

Total cases: 111

## Composite Score
- average: 95.62

## Score Breakdown
- leakage_fraction: 0.04
- privacy: 95.75
- quality: 95.50
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 4.216 | 1.373 | 20.061 |
| call_untrusted | 12.693 | 12.190 | 23.787 |
| reconstruct_response | 13.894 | 13.026 | 27.839 |
| **Total** | **30.803** | **27.683** | **60.230** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 13 |
