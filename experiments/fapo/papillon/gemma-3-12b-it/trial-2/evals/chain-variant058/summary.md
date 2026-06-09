# Evaluation Summary

Total cases: 111

## Composite Score
- average: 95.22

## Score Breakdown
- leakage_fraction: 0.05
- privacy: 94.94
- quality: 95.50
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 4.188 | 1.301 | 20.395 |
| call_untrusted | 13.903 | 11.603 | 27.570 |
| reconstruct_response | 12.515 | 11.577 | 30.703 |
| **Total** | **30.607** | **26.298** | **72.354** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 15 |
