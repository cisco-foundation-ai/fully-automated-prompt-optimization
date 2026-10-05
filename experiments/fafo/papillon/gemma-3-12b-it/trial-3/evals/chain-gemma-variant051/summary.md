# Evaluation Summary

Total cases: 111

## Composite Score
- average: 97.13

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 96.97
- quality: 97.30
- quality_passed: 0.97

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.688 | 1.342 | 17.656 |
| call_untrusted | 12.616 | 12.494 | 29.273 |
| reconstruct_response | 12.289 | 11.710 | 29.943 |
| **Total** | **28.594** | **26.915** | **59.798** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 9 |
