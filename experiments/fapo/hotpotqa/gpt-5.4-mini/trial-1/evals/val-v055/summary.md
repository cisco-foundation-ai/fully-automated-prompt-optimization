# Evaluation Summary

Total cases: 300

## Composite Score
- average: 66.67

## Score Breakdown
- exact_match: 66.67
- f1: 73.97

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.140 | 0.002 | 0.123 |
| summarize_hop1 | 1.419 | 1.267 | 2.152 |
| query_hop2 | 1.599 | 1.048 | 1.824 |
| retrieve_hop2 | 0.473 | 0.002 | 1.645 |
| summarize_hop2 | 1.577 | 1.514 | 2.268 |
| answer | 0.843 | 0.783 | 1.273 |
| **Total** | **6.051** | **5.058** | **7.859** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 100 |
