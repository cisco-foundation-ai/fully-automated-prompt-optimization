# Evaluation Summary

Total cases: 111

## Composite Score
- average: 94.62

## Score Breakdown
- leakage_fraction: 0.04
- privacy: 96.44
- quality: 92.79
- quality_passed: 0.93

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.750 | 1.285 | 18.306 |
| call_untrusted | 12.152 | 11.815 | 22.435 |
| reconstruct_response | 12.524 | 11.724 | 25.606 |
| **Total** | **28.426** | **26.704** | **56.963** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 16 |
