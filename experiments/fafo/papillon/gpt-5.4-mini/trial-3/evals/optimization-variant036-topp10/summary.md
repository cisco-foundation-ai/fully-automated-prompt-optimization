# Evaluation Summary

Total cases: 111

## Composite Score
- average: 96.32

## Score Breakdown
- leakage_fraction: 0.04
- privacy: 96.25
- quality: 96.40
- quality_passed: 0.96

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 2.233 | 1.072 | 7.293 |
| call_untrusted | 3.858 | 2.202 | 12.636 |
| reconstruct_response | 2.428 | 1.477 | 7.676 |
| **Total** | **8.518** | **5.622** | **27.105** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 10 |
