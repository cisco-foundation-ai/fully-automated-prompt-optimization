# Evaluation Summary

Total cases: 111

## Composite Score
- average: 97.22

## Score Breakdown
- leakage_fraction: 0.05
- privacy: 95.35
- quality: 99.10
- quality_passed: 0.99

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 2.879 | 1.226 | 7.937 |
| call_untrusted | 3.919 | 2.044 | 13.640 |
| reconstruct_response | 2.831 | 1.646 | 9.263 |
| **Total** | **9.629** | **5.611** | **26.656** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 8 |
