# Evaluation Summary

Total cases: 300

## Composite Score
- average: 65.67

## Score Breakdown
- exact_match: 65.67
- f1: 73.37

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.002 | 0.002 | 0.003 |
| summarize_hop1 | 4.844 | 4.405 | 8.416 |
| query_hop2 | 2.173 | 1.929 | 3.727 |
| retrieve_hop2 | 0.537 | 0.096 | 1.497 |
| summarize_hop2 | 4.718 | 3.994 | 7.909 |
| answer | 2.813 | 2.276 | 5.745 |
| **Total** | **15.088** | **14.277** | **23.325** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 103 |
