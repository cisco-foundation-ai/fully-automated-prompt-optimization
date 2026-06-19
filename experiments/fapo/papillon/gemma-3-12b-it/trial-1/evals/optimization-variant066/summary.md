# Evaluation Summary

Total cases: 111

## Composite Score
- average: 94.42

## Score Breakdown
- leakage_fraction: 0.06
- privacy: 94.24
- quality: 94.59
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.969 | 1.331 | 20.557 |
| call_untrusted | 12.718 | 11.715 | 25.499 |
| reconstruct_response | 12.791 | 11.632 | 28.411 |
| **Total** | **29.479** | **25.961** | **61.163** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 17 |
