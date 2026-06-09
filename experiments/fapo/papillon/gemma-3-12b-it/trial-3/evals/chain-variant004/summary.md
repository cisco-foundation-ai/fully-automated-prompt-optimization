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
| redact_query | 4.783 | 1.504 | 18.784 |
| call_untrusted | 6.705 | 2.537 | 26.529 |
| reconstruct_response | 5.789 | 2.450 | 20.899 |
| **Total** | **17.277** | **6.735** | **61.985** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 10 |
