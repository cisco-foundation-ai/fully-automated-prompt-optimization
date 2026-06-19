# Evaluation Summary

Total cases: 111

## Composite Score
- average: 97.62

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 97.04
- quality: 98.20
- quality_passed: 0.98

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.706 | 1.275 | 17.547 |
| call_untrusted | 15.946 | 15.697 | 26.111 |
| reconstruct_response | 16.631 | 15.900 | 29.283 |
| **Total** | **36.283** | **35.227** | **59.949** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 7 |
