# Evaluation Summary

Total cases: 300

## Composite Score
- average: 71.00

## Score Breakdown
- exact_match: 71.00
- f1: 79.05

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.021 | 0.002 | 0.009 |
| summarize_hop1 | 5.606 | 4.771 | 10.790 |
| query_hop2 | 2.464 | 2.088 | 3.928 |
| retrieve_hop2 | 0.337 | 0.002 | 1.279 |
| summarize_hop2 | 4.005 | 3.538 | 6.134 |
| answer | 2.329 | 2.131 | 3.927 |
| **Total** | **14.762** | **13.399** | **24.493** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 87 |
