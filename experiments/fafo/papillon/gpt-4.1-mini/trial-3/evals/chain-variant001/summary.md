# Evaluation Summary

Total cases: 111

## Composite Score
- average: 72.51

## Score Breakdown
- leakage_fraction: 0.50
- privacy: 49.53
- quality: 95.50
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 5.511 | 2.494 | 22.244 |
| call_untrusted | 6.208 | 3.593 | 18.246 |
| reconstruct_response | 6.696 | 4.217 | 19.934 |
| **Total** | **18.415** | **13.274** | **54.669** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 68 |
