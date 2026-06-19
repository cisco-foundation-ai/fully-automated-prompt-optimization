# Evaluation Summary

Total cases: 111

## Composite Score
- average: 96.28

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 97.06
- quality: 95.50
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 10.580 | 1.598 | 25.674 |
| call_untrusted | 11.835 | 11.270 | 22.715 |
| reconstruct_response | 12.303 | 10.287 | 21.917 |
| **Total** | **34.718** | **24.784** | **102.225** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 11 |
