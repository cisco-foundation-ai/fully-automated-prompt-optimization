# Evaluation Summary

Total cases: 111

## Composite Score
- average: 97.58

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 96.97
- quality: 98.20
- quality_passed: 0.98

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.663 | 1.388 | 17.456 |
| call_untrusted | 16.025 | 15.464 | 26.762 |
| reconstruct_response | 16.523 | 16.173 | 29.272 |
| **Total** | **36.211** | **34.353** | **60.551** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 8 |
