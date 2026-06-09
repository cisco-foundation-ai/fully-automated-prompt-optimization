# Evaluation Summary

Total cases: 111

## Composite Score
- average: 96.80

## Score Breakdown
- leakage_fraction: 0.04
- privacy: 96.30
- quality: 97.30
- quality_passed: 0.97

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 4.649 | 1.364 | 18.271 |
| call_untrusted | 13.430 | 11.951 | 28.236 |
| reconstruct_response | 14.650 | 13.536 | 31.136 |
| **Total** | **32.729** | **28.568** | **67.606** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 11 |
