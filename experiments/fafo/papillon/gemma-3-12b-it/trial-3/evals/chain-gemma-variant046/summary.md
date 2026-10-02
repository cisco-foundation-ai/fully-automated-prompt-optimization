# Evaluation Summary

Total cases: 111

## Composite Score
- average: 96.29

## Score Breakdown
- leakage_fraction: 0.05
- privacy: 95.28
- quality: 97.30
- quality_passed: 0.97

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 5.179 | 1.795 | 29.573 |
| call_untrusted | 15.730 | 13.975 | 44.728 |
| reconstruct_response | 15.068 | 13.369 | 37.022 |
| **Total** | **35.978** | **31.642** | **99.477** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 12 |
