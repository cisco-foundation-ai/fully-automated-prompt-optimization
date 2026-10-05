# Evaluation Summary

Total cases: 150

## Composite Score
- average: 68.67

## Score Breakdown
- exact_match: 68.67
- f1: 73.44

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.054 | 0.002 | 0.044 |
| summarize_hop1 | 2.296 | 2.133 | 3.835 |
| query_hop2 | 1.224 | 1.208 | 1.751 |
| retrieve_hop2 | 0.593 | 0.002 | 1.556 |
| summarize_hop2 | 2.198 | 2.048 | 3.309 |
| answer | 0.745 | 0.683 | 1.145 |
| **Total** | **7.111** | **6.498** | **10.605** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 47 |
