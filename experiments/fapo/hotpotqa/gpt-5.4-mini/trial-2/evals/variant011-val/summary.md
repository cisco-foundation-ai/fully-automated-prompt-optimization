# Evaluation Summary

Total cases: 300

## Composite Score
- average: 69.67

## Score Breakdown
- exact_match: 69.67
- f1: 76.36

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.022 | 0.002 | 0.008 |
| summarize_hop1 | 2.141 | 2.019 | 3.213 |
| query_hop2 | 1.167 | 1.035 | 1.533 |
| retrieve_hop2 | 0.779 | 0.005 | 1.666 |
| summarize_hop2 | 1.765 | 1.691 | 2.479 |
| answer | 0.831 | 0.790 | 1.188 |
| **Total** | **6.705** | **6.249** | **9.094** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 91 |
