# Evaluation Summary

Total cases: 300

## Composite Score
- average: 65.33

## Score Breakdown
- exact_match: 65.33
- f1: 75.41

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.088 | 0.002 | 0.122 |
| summarize_hop1 | 1.345 | 1.266 | 2.031 |
| query_hop2 | 1.097 | 1.018 | 1.705 |
| retrieve_hop2 | 0.528 | 0.002 | 1.673 |
| summarize_hop2 | 1.571 | 1.474 | 2.340 |
| answer | 0.862 | 0.784 | 1.397 |
| **Total** | **5.492** | **4.876** | **7.725** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 104 |
