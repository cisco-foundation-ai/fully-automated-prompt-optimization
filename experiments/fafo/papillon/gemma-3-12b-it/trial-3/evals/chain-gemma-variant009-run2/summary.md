# Evaluation Summary

Total cases: 111

## Composite Score
- average: 96.43

## Score Breakdown
- leakage_fraction: 0.04
- privacy: 96.47
- quality: 96.40
- quality_passed: 0.96

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.658 | 1.248 | 16.775 |
| call_untrusted | 11.566 | 11.214 | 22.794 |
| reconstruct_response | 11.335 | 10.779 | 23.536 |
| **Total** | **26.560** | **24.639** | **54.354** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 12 |
