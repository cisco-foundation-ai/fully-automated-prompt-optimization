# Evaluation Summary

Total cases: 111

## Composite Score
- average: 95.35

## Score Breakdown
- leakage_fraction: 0.08
- privacy: 92.49
- quality: 98.20
- quality_passed: 0.98

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 2.588 | 1.369 | 9.279 |
| call_untrusted | 3.666 | 1.973 | 11.084 |
| reconstruct_response | 2.584 | 1.742 | 8.264 |
| **Total** | **8.839** | **5.745** | **24.433** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 15 |
