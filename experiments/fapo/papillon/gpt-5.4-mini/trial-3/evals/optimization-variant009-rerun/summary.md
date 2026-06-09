# Evaluation Summary

Total cases: 111

## Composite Score
- average: 96.32

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 97.15
- quality: 95.50
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 2.034 | 1.045 | 6.687 |
| call_untrusted | 2.754 | 1.719 | 8.662 |
| reconstruct_response | 1.968 | 1.290 | 5.821 |
| **Total** | **6.756** | **4.320** | **21.040** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 10 |
