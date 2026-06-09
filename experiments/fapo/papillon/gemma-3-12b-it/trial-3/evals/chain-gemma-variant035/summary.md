# Evaluation Summary

Total cases: 111

## Composite Score
- average: 96.05

## Score Breakdown
- leakage_fraction: 0.04
- privacy: 95.70
- quality: 96.40
- quality_passed: 0.96

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.687 | 1.143 | 17.211 |
| call_untrusted | 10.839 | 10.790 | 20.197 |
| reconstruct_response | 10.881 | 10.701 | 20.971 |
| **Total** | **25.406** | **24.508** | **50.975** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 13 |
