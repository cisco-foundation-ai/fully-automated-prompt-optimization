# Evaluation Summary

Total cases: 221

## Composite Score
- average: 95.56

## Score Breakdown
- leakage_fraction: 0.04
- privacy: 96.10
- quality: 95.02
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 1.962 | 1.220 | 7.138 |
| call_untrusted | 3.484 | 1.983 | 9.722 |
| reconstruct_response | 2.611 | 1.550 | 9.736 |
| **Total** | **8.057** | **5.587** | **26.089** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 27 |
