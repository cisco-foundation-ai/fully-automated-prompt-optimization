# Evaluation Summary

Total cases: 150

## Composite Score
- average: 72.67

## Score Breakdown
- exact_match: 72.67
- f1: 78.79

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.087 | 0.002 | 0.218 |
| summarize_hop1 | 1.620 | 1.552 | 2.226 |
| query_hop2 | 1.049 | 1.012 | 1.336 |
| retrieve_hop2 | 0.502 | 0.002 | 1.612 |
| summarize_hop2 | 1.576 | 1.490 | 2.292 |
| answer | 0.786 | 0.758 | 1.119 |
| **Total** | **5.621** | **5.320** | **7.702** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 41 |
