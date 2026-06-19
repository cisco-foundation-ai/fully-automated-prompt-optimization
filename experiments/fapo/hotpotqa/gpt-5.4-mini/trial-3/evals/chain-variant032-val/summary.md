# Evaluation Summary

Total cases: 300

## Composite Score
- average: 72.67

## Score Breakdown
- exact_match: 72.67
- f1: 79.85

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.054 | 0.002 | 0.008 |
| summarize_hop1 | 1.216 | 1.160 | 1.703 |
| query_hop2 | 1.067 | 1.011 | 1.549 |
| retrieve_hop2 | 0.349 | 0.002 | 1.594 |
| summarize_hop2 | 1.298 | 1.207 | 1.619 |
| answer | 1.023 | 0.882 | 1.535 |
| **Total** | **5.008** | **4.501** | **6.816** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 82 |
