# Evaluation Summary

Total cases: 111

## Composite Score
- average: 94.22

## Score Breakdown
- leakage_fraction: 0.05
- privacy: 94.74
- quality: 93.69
- quality_passed: 0.94

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 2.247 | 1.071 | 7.192 |
| call_untrusted | 3.781 | 1.905 | 14.173 |
| reconstruct_response | 2.543 | 1.422 | 8.234 |
| **Total** | **8.571** | **5.387** | **23.056** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 16 |
