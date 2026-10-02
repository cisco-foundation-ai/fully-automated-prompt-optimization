# Evaluation Summary

Total cases: 111

## Composite Score
- average: 95.50

## Score Breakdown
- leakage_fraction: 0.00
- privacy: 100.00
- quality: 90.99
- quality_passed: 0.91

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 1.778 | 1.106 | 6.589 |
| call_untrusted | 3.546 | 1.775 | 16.172 |
| reconstruct_response | 2.704 | 1.453 | 11.236 |
| **Total** | **8.028** | **4.795** | **26.408** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 10 |
