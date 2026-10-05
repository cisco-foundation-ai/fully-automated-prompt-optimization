# Evaluation Summary

Total cases: 111

## Composite Score
- average: 97.20

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 97.10
- quality: 97.30
- quality_passed: 0.97

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.349 | 1.221 | 16.335 |
| call_untrusted | 11.423 | 11.448 | 20.617 |
| reconstruct_response | 12.649 | 11.633 | 23.660 |
| **Total** | **27.420** | **26.433** | **54.080** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 9 |
