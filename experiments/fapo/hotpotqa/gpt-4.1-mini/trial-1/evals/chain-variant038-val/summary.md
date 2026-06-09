# Evaluation Summary

Total cases: 300

## Composite Score
- average: 69.67

## Score Breakdown
- exact_match: 69.67
- f1: 77.02

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.030 | 0.002 | 0.007 |
| summarize_hop1 | 3.114 | 2.765 | 5.518 |
| query_hop2 | 1.891 | 1.627 | 3.486 |
| retrieve_hop2 | 0.230 | 0.002 | 1.116 |
| summarize_hop2 | 2.742 | 2.585 | 4.275 |
| answer | 1.723 | 1.468 | 3.025 |
| **Total** | **9.731** | **9.118** | **14.415** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 91 |
