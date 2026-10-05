# Evaluation Summary

Total cases: 300

## Composite Score
- average: 72.33

## Score Breakdown
- exact_match: 72.33
- f1: 79.63

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.015 | 0.002 | 0.008 |
| summarize_hop1 | 1.526 | 1.438 | 2.145 |
| query_hop2 | 1.010 | 0.951 | 1.411 |
| retrieve_hop2 | 0.734 | 0.003 | 1.514 |
| summarize_hop2 | 1.341 | 1.192 | 1.809 |
| answer | 0.923 | 0.859 | 1.422 |
| **Total** | **5.548** | **5.159** | **7.031** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 82 |
| query_hop2 | 1 |
