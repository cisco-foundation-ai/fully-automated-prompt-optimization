# Evaluation Summary

Total cases: 221

## Composite Score
- average: 95.35

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 97.48
- quality: 93.21
- quality_passed: 0.93

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.642 | 1.668 | 13.151 |
| call_untrusted | 4.194 | 2.639 | 13.929 |
| reconstruct_response | 4.440 | 2.876 | 13.761 |
| **Total** | **12.275** | **8.346** | **36.275** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 25 |
