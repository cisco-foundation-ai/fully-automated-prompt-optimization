# Evaluation Summary

Total cases: 111

## Composite Score
- average: 96.70

## Score Breakdown
- leakage_fraction: 0.01
- privacy: 98.80
- quality: 94.59
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 2.239 | 1.176 | 7.664 |
| call_untrusted | 3.195 | 1.778 | 10.414 |
| reconstruct_response | 2.628 | 1.686 | 8.085 |
| **Total** | **8.063** | **5.013** | **24.218** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 8 |
