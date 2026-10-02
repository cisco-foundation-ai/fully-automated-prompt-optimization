# Evaluation Summary

Total cases: 111

## Composite Score
- average: 95.48

## Score Breakdown
- leakage_fraction: 0.05
- privacy: 94.56
- quality: 96.40
- quality_passed: 0.96

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.670 | 1.258 | 16.772 |
| call_untrusted | 12.282 | 11.658 | 23.586 |
| reconstruct_response | 13.938 | 13.117 | 28.603 |
| **Total** | **29.891** | **28.718** | **59.053** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 11 |
