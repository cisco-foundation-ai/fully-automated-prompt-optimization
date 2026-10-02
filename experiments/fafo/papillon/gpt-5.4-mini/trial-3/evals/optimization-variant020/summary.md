# Evaluation Summary

Total cases: 111

## Composite Score
- average: 94.89

## Score Breakdown
- leakage_fraction: 0.04
- privacy: 96.10
- quality: 93.69
- quality_passed: 0.94

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 1.868 | 1.176 | 5.569 |
| call_untrusted | 3.475 | 1.933 | 11.753 |
| reconstruct_response | 2.645 | 1.457 | 7.832 |
| **Total** | **7.987** | **4.571** | **22.146** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 13 |
