# Evaluation Summary

Total cases: 111

## Composite Score
- average: 95.12

## Score Breakdown
- leakage_fraction: 0.05
- privacy: 94.75
- quality: 95.50
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.901 | 1.216 | 19.365 |
| call_untrusted | 11.892 | 11.470 | 21.578 |
| reconstruct_response | 12.818 | 11.729 | 29.160 |
| **Total** | **28.611** | **25.877** | **58.711** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 15 |
