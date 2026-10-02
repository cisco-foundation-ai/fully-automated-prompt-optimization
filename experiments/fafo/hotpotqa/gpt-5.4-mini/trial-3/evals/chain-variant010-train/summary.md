# Evaluation Summary

Total cases: 150

## Composite Score
- average: 74.67

## Score Breakdown
- exact_match: 74.67
- f1: 81.80

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.062 | 0.002 | 0.023 |
| summarize_hop1 | 1.498 | 1.441 | 2.084 |
| query_hop2 | 1.056 | 0.960 | 1.753 |
| retrieve_hop2 | 0.694 | 0.002 | 1.678 |
| summarize_hop2 | 1.258 | 1.175 | 1.802 |
| answer | 0.940 | 0.881 | 1.271 |
| **Total** | **5.507** | **4.733** | **8.457** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 38 |
