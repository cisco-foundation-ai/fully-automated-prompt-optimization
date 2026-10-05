# Evaluation Summary

Total cases: 150

## Composite Score
- average: 74.67

## Score Breakdown
- exact_match: 74.67
- f1: 81.24

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.038 | 0.002 | 0.019 |
| summarize_hop1 | 1.580 | 1.437 | 2.084 |
| query_hop2 | 0.992 | 0.917 | 1.322 |
| retrieve_hop2 | 0.722 | 0.002 | 1.692 |
| summarize_hop2 | 1.330 | 1.208 | 1.630 |
| answer | 0.901 | 0.882 | 1.131 |
| **Total** | **5.564** | **4.777** | **7.501** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 38 |
