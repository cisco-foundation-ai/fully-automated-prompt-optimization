# Evaluation Summary

Total cases: 300

## Composite Score
- average: 68.67

## Score Breakdown
- exact_match: 68.67
- f1: 75.51

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.027 | 0.002 | 0.010 |
| summarize_hop1 | 2.399 | 2.144 | 3.660 |
| query_hop2 | 1.307 | 1.140 | 2.343 |
| retrieve_hop2 | 0.333 | 0.002 | 1.347 |
| summarize_hop2 | 1.791 | 1.602 | 2.699 |
| answer | 1.007 | 0.862 | 1.542 |
| **Total** | **6.864** | **6.232** | **10.634** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 94 |
