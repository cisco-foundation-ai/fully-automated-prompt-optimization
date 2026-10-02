# Evaluation Summary

Total cases: 111

## Composite Score
- average: 96.73

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 97.06
- quality: 96.40
- quality_passed: 0.96

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.732 | 1.275 | 18.713 |
| call_untrusted | 16.074 | 15.858 | 29.783 |
| reconstruct_response | 18.434 | 17.559 | 32.513 |
| **Total** | **38.240** | **36.348** | **73.404** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 8 |
