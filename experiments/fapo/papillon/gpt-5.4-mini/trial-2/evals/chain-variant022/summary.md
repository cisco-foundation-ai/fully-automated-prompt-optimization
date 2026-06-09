# Evaluation Summary

Total cases: 111

## Composite Score
- average: 94.85

## Score Breakdown
- leakage_fraction: 0.08
- privacy: 91.50
- quality: 98.20
- quality_passed: 0.98

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 2.371 | 1.222 | 7.919 |
| call_untrusted | 4.085 | 1.988 | 15.418 |
| reconstruct_response | 2.883 | 1.479 | 9.055 |
| **Total** | **9.339** | **5.291** | **26.889** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 16 |
