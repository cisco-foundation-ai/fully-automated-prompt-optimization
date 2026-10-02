# Evaluation Summary

Total cases: 111

## Composite Score
- average: 95.55

## Score Breakdown
- leakage_fraction: 0.06
- privacy: 93.80
- quality: 97.30
- quality_passed: 0.97

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 4.226 | 1.483 | 20.158 |
| call_untrusted | 13.622 | 11.671 | 32.961 |
| reconstruct_response | 13.817 | 12.288 | 27.618 |
| **Total** | **31.665** | **26.216** | **66.299** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 13 |
