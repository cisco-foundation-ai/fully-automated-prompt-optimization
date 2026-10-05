# Evaluation Summary

Total cases: 111

## Composite Score
- average: 94.52

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 97.15
- quality: 91.89
- quality_passed: 0.92

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 4.838 | 1.604 | 21.409 |
| call_untrusted | 7.246 | 3.484 | 22.825 |
| reconstruct_response | 7.547 | 4.313 | 22.423 |
| **Total** | **19.631** | **11.197** | **69.237** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 14 |
