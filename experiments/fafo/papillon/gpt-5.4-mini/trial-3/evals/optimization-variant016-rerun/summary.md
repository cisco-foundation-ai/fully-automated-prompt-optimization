# Evaluation Summary

Total cases: 111

## Composite Score
- average: 96.77

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 97.15
- quality: 96.40
- quality_passed: 0.96

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 1.951 | 1.071 | 6.956 |
| call_untrusted | 3.571 | 1.912 | 11.961 |
| reconstruct_response | 2.265 | 1.466 | 6.128 |
| **Total** | **7.787** | **4.802** | **26.537** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 9 |
