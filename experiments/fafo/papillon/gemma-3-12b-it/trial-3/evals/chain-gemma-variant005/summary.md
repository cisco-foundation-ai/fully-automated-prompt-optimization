# Evaluation Summary

Total cases: 111

## Composite Score
- average: 93.72

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 97.36
- quality: 90.09
- quality_passed: 0.90

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 8.815 | 1.580 | 22.426 |
| call_untrusted | 11.666 | 11.511 | 22.133 |
| reconstruct_response | 12.446 | 11.003 | 21.671 |
| **Total** | **32.926** | **25.671** | **72.924** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 15 |
