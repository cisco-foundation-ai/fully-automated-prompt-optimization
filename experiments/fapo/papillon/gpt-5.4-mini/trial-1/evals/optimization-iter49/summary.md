# Evaluation Summary

Total cases: 111

## Composite Score
- average: 95.12

## Score Breakdown
- leakage_fraction: 0.04
- privacy: 95.65
- quality: 94.59
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 2.126 | 1.299 | 7.152 |
| call_untrusted | 4.197 | 2.151 | 14.576 |
| reconstruct_response | 3.209 | 1.700 | 10.775 |
| **Total** | **9.533** | **6.047** | **27.275** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 13 |
