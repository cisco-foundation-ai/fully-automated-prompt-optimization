# Evaluation Summary

Total cases: 111

## Composite Score
- average: 94.99

## Score Breakdown
- leakage_fraction: 0.06
- privacy: 94.48
- quality: 95.50
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 2.279 | 1.126 | 7.757 |
| call_untrusted | 4.277 | 2.321 | 16.016 |
| reconstruct_response | 3.137 | 1.746 | 10.140 |
| **Total** | **9.693** | **5.793** | **27.113** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 17 |
