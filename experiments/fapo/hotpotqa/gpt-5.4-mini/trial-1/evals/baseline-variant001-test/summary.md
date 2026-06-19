# Evaluation Summary

Total cases: 300

## Composite Score
- average: 58.67

## Score Breakdown
- exact_match: 58.67
- f1: 69.01

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.019 | 0.002 | 0.009 |
| summarize_hop1 | 1.934 | 1.392 | 4.533 |
| query_hop2 | 1.539 | 1.177 | 3.319 |
| retrieve_hop2 | 1.107 | 1.308 | 1.634 |
| summarize_hop2 | 1.756 | 1.348 | 3.991 |
| answer | 3.658 | 1.190 | 3.114 |
| **Total** | **10.013** | **6.962** | **15.119** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 124 |
