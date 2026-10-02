# Evaluation Summary

Total cases: 300

## Composite Score
- average: 62.67

## Score Breakdown
- exact_match: 62.67
- f1: 69.13

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 1.013 | 1.079 | 1.641 |
| summarize_hop1 | 7.068 | 2.896 | 7.137 |
| query_hop2 | 3.698 | 1.272 | 5.261 |
| retrieve_hop2 | 1.093 | 1.246 | 1.587 |
| summarize_hop2 | 3.512 | 3.124 | 6.404 |
| answer | 3.916 | 1.304 | 4.727 |
| **Total** | **20.300** | **11.537** | **30.907** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 112 |
