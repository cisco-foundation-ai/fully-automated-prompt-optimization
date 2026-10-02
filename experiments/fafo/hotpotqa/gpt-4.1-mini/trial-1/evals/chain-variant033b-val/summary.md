# Evaluation Summary

Total cases: 300

## Composite Score
- average: 66.67

## Score Breakdown
- exact_match: 66.67
- f1: 74.32

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.028 | 0.002 | 0.009 |
| summarize_hop1 | 4.366 | 3.757 | 8.293 |
| query_hop2 | 2.073 | 1.835 | 3.738 |
| retrieve_hop2 | 0.245 | 0.002 | 1.439 |
| summarize_hop2 | 3.412 | 3.240 | 5.436 |
| answer | 1.845 | 1.710 | 2.724 |
| **Total** | **11.969** | **11.431** | **18.463** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 100 |
