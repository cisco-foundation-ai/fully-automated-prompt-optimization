# Evaluation Summary

Total cases: 111

## Composite Score
- average: 94.97

## Score Breakdown
- leakage_fraction: 0.04
- privacy: 96.25
- quality: 93.69
- quality_passed: 0.94

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 1.946 | 1.122 | 6.417 |
| call_untrusted | 3.352 | 1.927 | 10.616 |
| reconstruct_response | 2.423 | 1.427 | 7.417 |
| **Total** | **7.721** | **5.053** | **21.911** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 13 |
