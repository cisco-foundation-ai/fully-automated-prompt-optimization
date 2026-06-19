# Evaluation Summary

Total cases: 111

## Composite Score
- average: 93.53

## Score Breakdown
- leakage_fraction: 0.07
- privacy: 93.36
- quality: 93.69
- quality_passed: 0.94

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 2.073 | 1.018 | 7.777 |
| call_untrusted | 4.189 | 2.023 | 14.230 |
| reconstruct_response | 3.119 | 1.681 | 8.750 |
| **Total** | **9.381** | **5.497** | **25.022** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 20 |
