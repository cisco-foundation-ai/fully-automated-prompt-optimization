# Evaluation Summary

Total cases: 111

## Composite Score
- average: 95.62

## Score Breakdown
- leakage_fraction: 0.02
- privacy: 98.44
- quality: 92.79
- quality_passed: 0.93

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 2.444 | 1.181 | 10.037 |
| call_untrusted | 4.691 | 2.259 | 19.087 |
| reconstruct_response | 2.711 | 1.624 | 6.854 |
| **Total** | **9.847** | **5.571** | **28.274** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 12 |
