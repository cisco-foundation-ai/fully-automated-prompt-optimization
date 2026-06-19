# Evaluation Summary

Total cases: 111

## Composite Score
- average: 96.28

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 97.06
- quality: 95.50
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 7.937 | 1.687 | 24.542 |
| call_untrusted | 12.177 | 11.270 | 28.013 |
| reconstruct_response | 10.974 | 10.219 | 22.074 |
| **Total** | **31.088** | **24.988** | **76.388** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 11 |
