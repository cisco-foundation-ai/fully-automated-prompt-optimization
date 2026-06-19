# Evaluation Summary

Total cases: 111

## Composite Score
- average: 92.18

## Score Breakdown
- leakage_fraction: 0.06
- privacy: 94.28
- quality: 90.09
- quality_passed: 0.90

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 6.221 | 1.972 | 30.526 |
| call_untrusted | 6.319 | 3.446 | 20.995 |
| reconstruct_response | 5.819 | 3.592 | 16.615 |
| **Total** | **18.358** | **10.852** | **63.877** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 21 |
