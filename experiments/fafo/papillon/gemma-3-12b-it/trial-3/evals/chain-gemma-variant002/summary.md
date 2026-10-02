# Evaluation Summary

Total cases: 111

## Composite Score
- average: 94.37

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 96.85
- quality: 91.89
- quality_passed: 0.92

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 8.869 | 1.595 | 24.556 |
| call_untrusted | 11.377 | 10.925 | 23.493 |
| reconstruct_response | 12.335 | 10.455 | 25.385 |
| **Total** | **32.582** | **26.046** | **80.487** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 16 |
