# Evaluation Summary

Total cases: 111

## Composite Score
- average: 96.32

## Score Breakdown
- leakage_fraction: 0.05
- privacy: 95.35
- quality: 97.30
- quality_passed: 0.97

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 2.497 | 1.179 | 8.470 |
| call_untrusted | 3.644 | 2.208 | 11.550 |
| reconstruct_response | 2.419 | 1.541 | 8.815 |
| **Total** | **8.561** | **5.902** | **26.585** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 11 |
