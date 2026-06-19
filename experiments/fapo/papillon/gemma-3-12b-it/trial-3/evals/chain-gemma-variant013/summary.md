# Evaluation Summary

Total cases: 111

## Composite Score
- average: 94.65

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 96.52
- quality: 92.79
- quality_passed: 0.93

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.669 | 1.194 | 17.847 |
| call_untrusted | 11.829 | 11.624 | 21.757 |
| reconstruct_response | 11.595 | 11.588 | 23.629 |
| **Total** | **27.093** | **25.829** | **53.146** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 15 |
