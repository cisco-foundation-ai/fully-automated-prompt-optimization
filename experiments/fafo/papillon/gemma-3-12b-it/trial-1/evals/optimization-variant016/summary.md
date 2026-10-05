# Evaluation Summary

Total cases: 111

## Composite Score
- average: 95.75

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 96.91
- quality: 94.59
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.608 | 1.154 | 18.771 |
| call_untrusted | 11.391 | 10.861 | 21.342 |
| reconstruct_response | 11.741 | 10.971 | 23.955 |
| **Total** | **26.740** | **25.274** | **55.515** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 12 |
