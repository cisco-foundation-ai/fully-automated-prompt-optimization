# Evaluation Summary

Total cases: 111

## Composite Score
- average: 96.06

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 96.62
- quality: 95.50
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.758 | 1.127 | 19.600 |
| call_untrusted | 11.172 | 10.897 | 21.846 |
| reconstruct_response | 10.203 | 9.711 | 21.715 |
| **Total** | **25.133** | **25.167** | **47.459** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 13 |
