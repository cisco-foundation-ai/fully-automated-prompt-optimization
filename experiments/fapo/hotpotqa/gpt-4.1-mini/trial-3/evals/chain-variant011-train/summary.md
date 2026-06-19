# Evaluation Summary

Total cases: 150

## Composite Score
- average: 67.33

## Score Breakdown
- exact_match: 67.33
- f1: 74.48

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.016 | 0.002 | 0.013 |
| summarize_hop1 | 3.548 | 3.216 | 5.851 |
| query_hop2 | 2.179 | 1.829 | 4.524 |
| retrieve_hop2 | 0.847 | 0.091 | 1.733 |
| summarize_hop2 | 3.331 | 3.071 | 5.742 |
| answer | 1.213 | 1.131 | 1.809 |
| **Total** | **11.134** | **10.490** | **17.621** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 49 |
