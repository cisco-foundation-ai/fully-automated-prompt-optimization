# Evaluation Summary

Total cases: 300

## Composite Score
- average: 69.67

## Score Breakdown
- exact_match: 69.67
- f1: 76.36

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.143 | 0.002 | 0.134 |
| summarize_hop1 | 1.363 | 1.292 | 2.012 |
| query_hop2 | 1.165 | 1.082 | 1.757 |
| retrieve_hop2 | 0.364 | 0.002 | 1.644 |
| summarize_hop2 | 1.659 | 1.570 | 2.461 |
| answer | 0.800 | 0.754 | 1.301 |
| **Total** | **5.493** | **4.895** | **8.348** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 91 |
