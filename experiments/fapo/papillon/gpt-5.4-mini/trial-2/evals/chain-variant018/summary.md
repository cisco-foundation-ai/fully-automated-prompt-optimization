# Evaluation Summary

Total cases: 111

## Composite Score
- average: 95.87

## Score Breakdown
- leakage_fraction: 0.06
- privacy: 93.54
- quality: 98.20
- quality_passed: 0.98

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 2.147 | 1.266 | 6.497 |
| call_untrusted | 4.526 | 2.398 | 17.362 |
| reconstruct_response | 3.271 | 1.779 | 11.621 |
| **Total** | **9.944** | **6.338** | **30.852** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 14 |
