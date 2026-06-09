# Evaluation Summary

Total cases: 111

## Composite Score
- average: 95.08

## Score Breakdown
- leakage_fraction: 0.04
- privacy: 96.46
- quality: 93.69
- quality_passed: 0.94

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.636 | 1.293 | 16.943 |
| call_untrusted | 11.561 | 11.838 | 19.478 |
| reconstruct_response | 11.303 | 11.620 | 21.233 |
| **Total** | **26.500** | **25.472** | **46.064** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 12 |
