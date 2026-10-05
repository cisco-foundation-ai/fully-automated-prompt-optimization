# Evaluation Summary

Total cases: 111

## Composite Score
- average: 92.06

## Score Breakdown
- leakage_fraction: 0.11
- privacy: 88.63
- quality: 95.50
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 4.268 | 1.686 | 16.762 |
| call_untrusted | 6.914 | 4.111 | 23.009 |
| reconstruct_response | 8.731 | 4.546 | 30.725 |
| **Total** | **19.912** | **12.185** | **59.676** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 23 |
