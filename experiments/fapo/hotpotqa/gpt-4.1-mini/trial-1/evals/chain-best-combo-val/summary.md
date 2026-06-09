# Evaluation Summary

Total cases: 300

## Composite Score
- average: 68.67

## Score Breakdown
- exact_match: 68.67
- f1: 76.16

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.009 | 0.002 | 0.006 |
| summarize_hop1 | 3.398 | 3.026 | 6.080 |
| query_hop2 | 1.713 | 1.567 | 2.714 |
| retrieve_hop2 | 1.694 | 1.603 | 1.675 |
| summarize_hop2 | 2.539 | 2.311 | 3.966 |
| answer | 1.500 | 1.356 | 2.426 |
| **Total** | **10.853** | **10.300** | **15.573** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 94 |
