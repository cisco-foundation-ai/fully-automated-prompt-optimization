# Evaluation Summary

Total cases: 300

## Composite Score
- average: 67.00

## Score Breakdown
- exact_match: 67.00
- f1: 73.91

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.023 | 0.002 | 0.008 |
| summarize_hop1 | 1.861 | 1.798 | 2.727 |
| query_hop2 | 1.213 | 1.138 | 1.750 |
| retrieve_hop2 | 0.521 | 0.002 | 1.631 |
| summarize_hop2 | 1.830 | 1.692 | 2.895 |
| answer | 0.934 | 0.843 | 1.418 |
| **Total** | **6.382** | **5.806** | **9.383** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 99 |
