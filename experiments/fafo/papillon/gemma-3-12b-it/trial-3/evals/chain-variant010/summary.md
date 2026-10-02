# Evaluation Summary

Total cases: 111

## Composite Score
- average: 96.18

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 96.87
- quality: 95.50
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 6.187 | 2.005 | 28.269 |
| call_untrusted | 8.041 | 3.768 | 22.977 |
| reconstruct_response | 8.041 | 4.316 | 24.968 |
| **Total** | **22.269** | **11.284** | **75.929** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 10 |
