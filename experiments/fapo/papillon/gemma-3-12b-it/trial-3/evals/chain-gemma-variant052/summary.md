# Evaluation Summary

Total cases: 111

## Composite Score
- average: 95.38

## Score Breakdown
- leakage_fraction: 0.04
- privacy: 96.17
- quality: 94.59
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.633 | 1.276 | 16.825 |
| call_untrusted | 12.244 | 12.314 | 24.354 |
| reconstruct_response | 11.772 | 11.873 | 22.639 |
| **Total** | **27.649** | **27.155** | **58.518** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 14 |
