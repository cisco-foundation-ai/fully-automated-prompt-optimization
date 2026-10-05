# Evaluation Summary

Total cases: 111

## Composite Score
- average: 94.55

## Score Breakdown
- leakage_fraction: 0.07
- privacy: 92.70
- quality: 96.40
- quality_passed: 0.96

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.583 | 1.328 | 12.759 |
| call_untrusted | 3.471 | 1.925 | 11.294 |
| reconstruct_response | 2.711 | 1.481 | 8.450 |
| **Total** | **9.765** | **5.832** | **27.081** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 17 |
