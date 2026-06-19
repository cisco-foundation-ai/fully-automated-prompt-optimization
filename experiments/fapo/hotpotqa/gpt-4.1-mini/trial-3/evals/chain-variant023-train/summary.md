# Evaluation Summary

Total cases: 150

## Composite Score
- average: 72.67

## Score Breakdown
- exact_match: 72.67
- f1: 79.14

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.005 | 0.002 | 0.009 |
| summarize_hop1 | 4.961 | 4.196 | 9.160 |
| query_hop2 | 2.146 | 1.960 | 3.796 |
| retrieve_hop2 | 1.493 | 1.537 | 1.657 |
| summarize_hop2 | 4.740 | 3.966 | 7.246 |
| answer | 2.120 | 1.990 | 3.302 |
| **Total** | **15.465** | **14.018** | **27.331** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 41 |
