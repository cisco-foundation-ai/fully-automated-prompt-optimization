# Evaluation Summary

Total cases: 111

## Composite Score
- average: 96.32

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 97.15
- quality: 95.50
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 4.978 | 2.009 | 25.278 |
| call_untrusted | 7.247 | 4.080 | 26.735 |
| reconstruct_response | 9.232 | 5.987 | 25.447 |
| **Total** | **21.458** | **13.084** | **67.134** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 9 |
