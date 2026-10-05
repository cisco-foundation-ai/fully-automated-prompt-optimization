# Evaluation Summary

Total cases: 111

## Composite Score
- average: 95.30

## Score Breakdown
- leakage_fraction: 0.07
- privacy: 93.30
- quality: 97.30
- quality_passed: 0.97

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 2.559 | 1.284 | 8.720 |
| call_untrusted | 5.123 | 2.508 | 20.116 |
| reconstruct_response | 3.609 | 1.928 | 12.037 |
| **Total** | **11.291** | **6.142** | **36.892** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 16 |
