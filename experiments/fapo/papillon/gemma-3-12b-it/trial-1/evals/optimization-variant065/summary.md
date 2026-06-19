# Evaluation Summary

Total cases: 111

## Composite Score
- average: 95.68

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 96.76
- quality: 94.59
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.881 | 1.256 | 20.655 |
| call_untrusted | 11.817 | 12.173 | 21.269 |
| reconstruct_response | 12.241 | 11.789 | 23.289 |
| **Total** | **27.939** | **25.587** | **58.563** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 12 |
