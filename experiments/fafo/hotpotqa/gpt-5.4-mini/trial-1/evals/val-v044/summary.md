# Evaluation Summary

Total cases: 300

## Composite Score
- average: 69.67

## Score Breakdown
- exact_match: 69.67
- f1: 76.97

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.160 | 0.002 | 0.121 |
| summarize_hop1 | 1.375 | 1.280 | 2.062 |
| query_hop2 | 1.101 | 1.054 | 1.538 |
| retrieve_hop2 | 0.273 | 0.002 | 1.353 |
| summarize_hop2 | 1.664 | 1.538 | 2.608 |
| answer | 0.776 | 0.733 | 1.162 |
| **Total** | **5.349** | **4.780** | **8.466** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 91 |
