# Evaluation Summary

Total cases: 111

## Composite Score
- average: 95.39

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 97.09
- quality: 93.69
- quality_passed: 0.94

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 5.453 | 1.990 | 24.519 |
| call_untrusted | 8.766 | 4.763 | 25.378 |
| reconstruct_response | 9.727 | 6.614 | 26.288 |
| **Total** | **23.946** | **14.811** | **94.470** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 12 |
