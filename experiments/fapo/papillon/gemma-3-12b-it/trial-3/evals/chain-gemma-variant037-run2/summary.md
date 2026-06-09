# Evaluation Summary

Total cases: 111

## Composite Score
- average: 96.23

## Score Breakdown
- leakage_fraction: 0.04
- privacy: 96.07
- quality: 96.40
- quality_passed: 0.96

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 5.280 | 1.283 | 17.408 |
| call_untrusted | 12.189 | 11.993 | 25.884 |
| reconstruct_response | 11.808 | 11.075 | 23.709 |
| **Total** | **29.276** | **26.231** | **63.000** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 12 |
