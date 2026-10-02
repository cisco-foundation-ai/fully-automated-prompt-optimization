# Evaluation Summary

Total cases: 300

## Composite Score
- average: 65.67

## Score Breakdown
- exact_match: 65.67
- f1: 74.32

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.003 | 0.003 | 0.005 |
| summarize_hop1 | 5.521 | 4.919 | 10.749 |
| query_hop2 | 2.466 | 2.114 | 4.319 |
| retrieve_hop2 | 0.507 | 0.106 | 1.539 |
| summarize_hop2 | 4.331 | 3.934 | 7.240 |
| answer | 2.360 | 2.075 | 4.233 |
| **Total** | **15.187** | **14.168** | **23.819** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 103 |
