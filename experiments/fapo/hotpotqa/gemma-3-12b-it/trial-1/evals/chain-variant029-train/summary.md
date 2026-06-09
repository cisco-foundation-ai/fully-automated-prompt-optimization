# Evaluation Summary

Total cases: 150

## Composite Score
- average: 74.00

## Score Breakdown
- exact_match: 74.00
- f1: 80.50

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.054 | 0.003 | 0.057 |
| summarize_hop1 | 2.295 | 2.074 | 4.166 |
| query_hop2 | 1.038 | 1.002 | 1.566 |
| retrieve_hop2 | 0.494 | 0.003 | 1.602 |
| summarize_hop2 | 2.275 | 2.147 | 3.549 |
| answer | 1.020 | 0.994 | 1.466 |
| **Total** | **7.176** | **6.721** | **10.229** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 39 |
