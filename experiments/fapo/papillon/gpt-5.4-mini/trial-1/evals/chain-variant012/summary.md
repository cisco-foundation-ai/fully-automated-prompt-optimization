# Evaluation Summary

Total cases: 111

## Composite Score
- average: 92.78

## Score Breakdown
- leakage_fraction: 0.05
- privacy: 94.58
- quality: 90.99
- quality_passed: 0.91

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 2.406 | 1.279 | 6.925 |
| call_untrusted | 3.571 | 1.911 | 12.216 |
| reconstruct_response | 2.676 | 1.501 | 8.714 |
| **Total** | **8.654** | **5.187** | **24.853** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 18 |
