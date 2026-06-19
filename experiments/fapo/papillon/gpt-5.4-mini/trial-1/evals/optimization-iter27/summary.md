# Evaluation Summary

Total cases: 111

## Composite Score
- average: 95.50

## Score Breakdown
- leakage_fraction: 0.05
- privacy: 94.59
- quality: 96.40
- quality_passed: 0.96

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 2.277 | 1.299 | 6.711 |
| call_untrusted | 3.662 | 2.234 | 10.074 |
| reconstruct_response | 2.798 | 1.644 | 8.208 |
| **Total** | **8.738** | **5.286** | **26.840** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 13 |
