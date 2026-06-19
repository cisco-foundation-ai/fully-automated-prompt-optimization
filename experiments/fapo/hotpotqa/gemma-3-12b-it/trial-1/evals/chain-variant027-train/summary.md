# Evaluation Summary

Total cases: 150

## Composite Score
- average: 70.00

## Score Breakdown
- exact_match: 70.00
- f1: 75.13

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.072 | 0.002 | 0.032 |
| summarize_hop1 | 2.461 | 2.291 | 4.189 |
| query_hop2 | 1.047 | 1.017 | 1.429 |
| retrieve_hop2 | 0.515 | 0.003 | 1.623 |
| summarize_hop2 | 2.565 | 2.469 | 3.863 |
| answer | 1.023 | 0.971 | 1.566 |
| **Total** | **7.683** | **7.287** | **11.142** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 45 |
