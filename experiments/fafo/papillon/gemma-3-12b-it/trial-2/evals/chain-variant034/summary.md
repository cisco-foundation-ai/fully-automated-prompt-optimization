# Evaluation Summary

Total cases: 111

## Composite Score
- average: 93.32

## Score Breakdown
- leakage_fraction: 0.06
- privacy: 93.84
- quality: 92.79
- quality_passed: 0.93

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.423 | 1.157 | 15.876 |
| call_untrusted | 12.021 | 11.769 | 23.273 |
| reconstruct_response | 12.831 | 12.738 | 26.153 |
| **Total** | **28.276** | **27.143** | **59.579** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 17 |
