# Evaluation Summary

Total cases: 300

## Composite Score
- average: 59.67

## Score Breakdown
- exact_match: 59.67
- f1: 66.75

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 1.064 | 0.678 | 1.682 |
| summarize_hop1 | 2.426 | 2.312 | 4.037 |
| query_hop2 | 1.070 | 1.031 | 1.577 |
| retrieve_hop2 | 1.217 | 1.493 | 1.630 |
| summarize_hop2 | 2.748 | 2.616 | 4.076 |
| answer | 1.111 | 1.050 | 1.689 |
| **Total** | **9.636** | **9.415** | **13.523** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 121 |
