# Evaluation Summary

Total cases: 111

## Composite Score
- average: 96.17

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 96.85
- quality: 95.50
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.396 | 1.023 | 16.225 |
| call_untrusted | 11.547 | 11.159 | 22.694 |
| reconstruct_response | 12.129 | 11.160 | 26.261 |
| **Total** | **27.072** | **24.728** | **56.531** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 12 |
