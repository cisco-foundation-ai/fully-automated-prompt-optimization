# Evaluation Summary

Total cases: 300

## Composite Score
- average: 68.67

## Score Breakdown
- exact_match: 68.67
- f1: 75.92

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.045 | 0.002 | 0.009 |
| summarize_hop1 | 2.418 | 2.180 | 3.720 |
| query_hop2 | 1.266 | 1.106 | 1.737 |
| retrieve_hop2 | 0.358 | 0.002 | 1.579 |
| summarize_hop2 | 1.831 | 1.722 | 2.703 |
| answer | 0.942 | 0.810 | 1.782 |
| **Total** | **6.859** | **6.245** | **10.062** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 94 |
