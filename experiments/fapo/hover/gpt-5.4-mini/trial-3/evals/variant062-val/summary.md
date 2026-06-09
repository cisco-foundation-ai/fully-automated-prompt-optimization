# Evaluation Summary

Total cases: 300

## Composite Score
- average: 67.67

## Score Breakdown
- num_found: 2.58
- num_gold: 3.00
- num_missing: 0.42
- partial_recall: 86.11
- recall: 67.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.952 | 0.538 | 1.705 |
| summarize_hop1 | 13.664 | 13.056 | 22.233 |
| query_hop2 | 0.944 | 0.790 | 1.299 |
| retrieve_hop2 | 1.040 | 1.076 | 1.623 |
| summarize_hop2 | 3.100 | 2.577 | 5.661 |
| query_hop3 | 0.925 | 0.782 | 1.323 |
| retrieve_hop3 | 1.159 | 1.101 | 1.643 |
| combine_retrievals | 0.000 | 0.000 | 0.001 |
| **Total** | **21.089** | **20.692** | **32.070** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 87 |
| retrieve_hop1 | 10 |
