# Evaluation Summary

Total cases: 150

## Composite Score
- average: 72.00

## Score Breakdown
- exact_match: 72.00
- f1: 78.30

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.091 | 0.002 | 0.078 |
| summarize_hop1 | 1.287 | 1.170 | 2.205 |
| query_hop2 | 1.027 | 0.923 | 1.855 |
| retrieve_hop2 | 0.584 | 0.002 | 1.611 |
| summarize_hop2 | 1.224 | 1.153 | 1.770 |
| answer | 0.883 | 0.857 | 1.186 |
| **Total** | **5.096** | **4.659** | **7.425** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 42 |
