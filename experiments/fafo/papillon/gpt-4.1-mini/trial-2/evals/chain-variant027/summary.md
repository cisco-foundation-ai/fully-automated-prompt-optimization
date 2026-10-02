# Evaluation Summary

Total cases: 111

## Composite Score
- average: 96.65

## Score Breakdown
- leakage_fraction: 0.04
- privacy: 96.00
- quality: 97.30
- quality_passed: 0.97

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 5.083 | 1.831 | 22.494 |
| call_untrusted | 7.661 | 3.567 | 23.046 |
| reconstruct_response | 8.913 | 3.726 | 33.218 |
| **Total** | **21.657** | **11.607** | **68.209** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 10 |
