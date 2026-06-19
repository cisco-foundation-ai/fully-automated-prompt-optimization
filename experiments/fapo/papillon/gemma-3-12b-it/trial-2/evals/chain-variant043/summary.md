# Evaluation Summary

Total cases: 111

## Composite Score
- average: 95.08

## Score Breakdown
- leakage_fraction: 0.05
- privacy: 94.65
- quality: 95.50
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.692 | 1.246 | 17.242 |
| call_untrusted | 11.199 | 10.339 | 21.389 |
| reconstruct_response | 12.185 | 11.562 | 23.975 |
| **Total** | **27.076** | **25.206** | **50.839** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 12 |
