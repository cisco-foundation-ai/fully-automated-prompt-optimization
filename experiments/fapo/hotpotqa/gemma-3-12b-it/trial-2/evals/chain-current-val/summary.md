# Evaluation Summary

Total cases: 300

## Composite Score
- average: 62.67

## Score Breakdown
- exact_match: 62.67
- f1: 69.89

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.023 | 0.002 | 0.012 |
| summarize_hop1 | 3.334 | 3.167 | 5.416 |
| query_hop2 | 1.209 | 1.150 | 1.774 |
| retrieve_hop2 | 0.579 | 0.003 | 1.620 |
| summarize_hop2 | 3.158 | 2.930 | 5.285 |
| answer | 1.008 | 0.916 | 1.590 |
| **Total** | **9.311** | **8.956** | **13.536** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 112 |
