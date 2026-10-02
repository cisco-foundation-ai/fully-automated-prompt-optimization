# Evaluation Summary

Total cases: 111

## Composite Score
- average: 95.59

## Score Breakdown
- leakage_fraction: 0.06
- privacy: 93.89
- quality: 97.30
- quality_passed: 0.97

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 5.182 | 1.305 | 18.163 |
| call_untrusted | 12.250 | 11.014 | 26.769 |
| reconstruct_response | 12.226 | 10.725 | 27.680 |
| **Total** | **29.658** | **25.337** | **64.607** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 12 |
