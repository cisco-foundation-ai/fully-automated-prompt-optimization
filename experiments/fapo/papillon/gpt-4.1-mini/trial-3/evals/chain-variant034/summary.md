# Evaluation Summary

Total cases: 111

## Composite Score
- average: 94.07

## Score Breakdown
- leakage_fraction: 0.04
- privacy: 96.25
- quality: 91.89
- quality_passed: 0.92

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 5.550 | 2.135 | 24.548 |
| call_untrusted | 8.824 | 4.814 | 28.420 |
| reconstruct_response | 9.253 | 5.415 | 31.791 |
| **Total** | **23.628** | **13.337** | **82.702** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 15 |
