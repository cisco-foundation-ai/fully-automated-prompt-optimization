# Evaluation Summary

Total cases: 111

## Composite Score
- average: 94.62

## Score Breakdown
- leakage_fraction: 0.05
- privacy: 94.64
- quality: 94.59
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 5.341 | 1.227 | 18.622 |
| call_untrusted | 12.495 | 11.072 | 27.397 |
| reconstruct_response | 14.105 | 13.013 | 30.635 |
| **Total** | **31.941** | **27.610** | **62.101** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 16 |
