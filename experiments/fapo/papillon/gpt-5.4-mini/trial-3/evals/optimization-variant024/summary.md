# Evaluation Summary

Total cases: 111

## Composite Score
- average: 94.97

## Score Breakdown
- leakage_fraction: 0.05
- privacy: 95.35
- quality: 94.59
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 2.178 | 1.129 | 7.732 |
| call_untrusted | 3.423 | 1.868 | 12.270 |
| reconstruct_response | 2.479 | 1.377 | 10.130 |
| **Total** | **8.080** | **4.754** | **27.224** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 13 |
