# Evaluation Summary

Total cases: 111

## Composite Score
- average: 96.20

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 96.90
- quality: 95.50
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.444 | 1.251 | 17.472 |
| call_untrusted | 11.693 | 11.301 | 22.565 |
| reconstruct_response | 11.613 | 11.377 | 22.581 |
| **Total** | **26.750** | **25.926** | **56.735** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 12 |
