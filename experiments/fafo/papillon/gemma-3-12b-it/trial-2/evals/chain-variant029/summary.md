# Evaluation Summary

Total cases: 111

## Composite Score
- average: 95.98

## Score Breakdown
- leakage_fraction: 0.06
- privacy: 93.75
- quality: 98.20
- quality_passed: 0.98

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 5.265 | 1.218 | 16.826 |
| call_untrusted | 12.310 | 11.937 | 21.905 |
| reconstruct_response | 13.088 | 12.066 | 27.368 |
| **Total** | **30.664** | **26.232** | **57.402** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 11 |
