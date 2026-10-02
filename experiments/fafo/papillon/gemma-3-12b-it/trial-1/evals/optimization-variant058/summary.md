# Evaluation Summary

Total cases: 111

## Composite Score
- average: 96.76

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 97.13
- quality: 96.40
- quality_passed: 0.96

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 4.630 | 1.620 | 18.316 |
| call_untrusted | 15.843 | 12.765 | 37.839 |
| reconstruct_response | 15.818 | 15.516 | 33.567 |
| **Total** | **36.291** | **32.920** | **76.227** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 10 |
