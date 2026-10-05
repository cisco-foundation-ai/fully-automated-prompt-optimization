# Evaluation Summary

Total cases: 111

## Composite Score
- average: 95.12

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 96.55
- quality: 93.69
- quality_passed: 0.94

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 1.814 | 1.069 | 6.147 |
| call_untrusted | 3.074 | 1.825 | 11.719 |
| reconstruct_response | 2.163 | 1.287 | 7.807 |
| **Total** | **7.051** | **4.548** | **21.410** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 12 |
