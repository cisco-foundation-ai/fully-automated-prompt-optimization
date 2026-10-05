# Evaluation Summary

Total cases: 111

## Composite Score
- average: 95.77

## Score Breakdown
- leakage_fraction: 0.06
- privacy: 94.24
- quality: 97.30
- quality_passed: 0.97

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 5.158 | 1.193 | 17.668 |
| call_untrusted | 13.352 | 12.406 | 25.422 |
| reconstruct_response | 13.510 | 12.813 | 27.400 |
| **Total** | **32.020** | **28.616** | **59.795** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 11 |
