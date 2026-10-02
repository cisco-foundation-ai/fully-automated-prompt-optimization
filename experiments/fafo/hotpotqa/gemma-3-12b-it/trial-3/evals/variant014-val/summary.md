# Evaluation Summary

Total cases: 300

## Composite Score
- average: 60.67

## Score Breakdown
- exact_match: 60.67
- f1: 70.31

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.038 | 0.002 | 0.013 |
| summarize_hop1 | 1.902 | 1.777 | 3.313 |
| query_hop2 | 0.994 | 0.947 | 1.395 |
| retrieve_hop2 | 0.748 | 0.014 | 1.651 |
| summarize_hop2 | 2.886 | 2.798 | 4.561 |
| answer | 1.073 | 1.026 | 1.562 |
| **Total** | **7.641** | **7.479** | **11.029** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 118 |
